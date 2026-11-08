# SCG4-REVIEW-ConsoleUxSortHelp（2026-11-09；鍵 `agentconsole-console-ux-sort-help`）

> 主控落檔說明：本檔由獨立 QA 鏡（Sonnet）在 scratchpad 寫成，一審（HEAD `fcb8959c`，判 FAIL：P1 0／P2 3／P3 1／P4 0；57 個有效突變存活 3）
> 與二審（HEAD `1c7cdd8a`，判 **PASS**：P1 0／P2 0／P3 0）兩段並存，**最終判定以文末〈I 二審〉為準**。
> 一審三條 P2 全為突變存活（測試鑑別力缺口）：F-01（專案卡片換排序不回第 1 頁）、F-02（SI 壞列排序方向）、F-03（事件表 seq tie-break）由原開發棒補斷言並經二審副本重放確認轉紅；
> P3 F-04（專案管理第 6 步把卡片「執行」連結說成按不了）由文案棒改句並經二審核實。接縫節勘誤候選（SortBar 換欄位沿用方向）登為 TCS 勘誤 E-12。
> 英文計數字樣（passed／skipped／tests）在本檔一律改為中文，以符合基線數字守門；數字本身未改。

# SCG-4 一審報告（QA 鏡，Sonnet）：鍵 agentconsole-console-ux-sort-help
審查基準：本機 HEAD `fcb8959c`；Oracle＝TCS-ConsoleUxSortHelp-20261108（含 §9 裁決）。全程唯讀；突變一律在 `git archive HEAD` 副本（前端副本因 Turbopack 拒收指向根外的 junction，改以 robocopy 複製 node_modules；backend 副本直接 gradlew）。

## A 摘要與判定
**判定：FAIL（P1 0／P2 3／P3 1／P4 0）**——三個 P2 全是「測試鑑別力缺口」（存活突變），產品行為本身在人讀與全套測試下皆正確。
- 單元／元件：`npx vitest run lib/domain/sorting.test.ts lib/domain/sortScope.static.test.ts components/domain lib/help lib/nav --reporter=verbose` rc=0，111 檔 1658 通過（當回合真跑）。
- 後端：副本 baseline `gradlew cleanTest test --tests *ProjectApiIT --tests *ImportFlowApiIT` rc=0（BUILD SUCCESSFUL 49s、83 個測試，含 AT_963_5_*）。
- E2E：副本 build（rc=0）後 `E2E_MODE=standalone` `npx playwright test console-sort.mock.spec.ts page-help.mock.spec.ts` rc=0、15 通過（2.4 分）。
- 持有面：`git diff --name-only 8e7cbabe..HEAD` 全在 §7.1 四包持有面與已知 E-6／E-1 內；`tools/**`、`.claude/**`、`AutoClaude/**`、`AISDLC_SDD/**`、`lib/domain/issues.ts`、`lib/domain/research.ts` 零差異。
- 突變：前端 25 個（3 存活）、FE-HELP 18 個（0 存活）、後端 8 個（0 存活）、E2E 6 個（0 存活）；共 57 個有效、3 存活。

## B 發現表
| 編號 | 級 | 內容 | 該補的斷言 |
|------|----|------|-----------|
| F-01 | P2 | 突變 S8（ProjectsView `filterKey` 拿掉 `sort.key,sort.dir`＝換排序不回第 1 頁）全套 vitest rc=0 存活。AT-963-4-1／W-UX5「換排序回第 1 頁」的 `page=0` 斷言是在本來就第 1 頁時比的，不可能失敗；ProjectsView 沒有 HistoryPanel 那種顯式 `setPaging` 兜底，`filterKey` 是唯一防線。 | ProjectsView.test.tsx：夾具 `totalPages>1`、按「下一頁」到第 2 頁後，改排序欄位（及按方向鈕）⇒ 下一個請求 `page=0`；另可加切「已刪除」模式亦回 `page=0`。 |
| F-02 | P2 | 突變 S11（SiObservationsPanel 壞列 `.sort((a,b)=>a.line-b.line)` 改反向）rc=0 存活。AT-963-3-5／W-UX3／QA F2 的「壞列彼此依 line 升冪」無鑑別：SiView 夾具只有 1 個壞列（`si-obs-invalid-` 計數皆 toHaveLength(1)）。 | SiView.test.tsx AT_963_3_5：夾具放 ≥2 個壞列且輸入序 line 降冪，斷言預設與點任一欄升／降冪後，壞列都在有效列之後且依 line 升冪。 |
| F-03 | P2 | 突變 S16（SiEventsPanel 拿掉 `tieBreak=EVENT_COLUMNS[0]`＝seq tie-break）rc=0 存活。T5 規格 tie-break＝seq、W-UX1(f)「全表無識別欄時用 tieBreak」；AT-963-3-7 事件夾具三列 kind／by／t 全相異，tie-break 從未被觸發。 | SiView.test.tsx AT_963_3_7：夾具加兩列 `kind`（或 `by`）相同、輸入序 seq 大者在前，點該欄升冪與降冪，斷言兩方向同值列都依 seq 升冪。 |
| F-04 | P3 | 文案事實不精確：`lib/help/projects.ts` 第 6 步「按卡片上的「執行」，按不了就先檢查有沒有審批」——ProjectCard 的「執行」是 `<Link>`（`ProjectCard.tsx:87`），永遠按得下去；擋住的是進入執行頁後的開始動作。建議改「進入執行頁後若無法開始，先檢查專案有沒有審批」。（主控若依「事實錯誤＝P2」可升級；我判 P3 因結論「無法執行→查審批」仍正確。） | — |
| F-05 | 資訊（不計級） | `lib/help/states.ts` 突變 H20（把第一個全形括號改半形）rc=0，但該字元疑落在註解而非語料，結果無資訊量，屬我的突變設計問題，不計缺陷；列出以示誠實。 | — |

## C AT 逐條表（測試 ＝ `檔::describe/測試名`；單跑＝上述整批 rc=0 且該名稱出現 ✓）
實作檔縮寫：SO＝`lib/domain/sorting.ts`、SH＝`components/domain/common/SortableHeader.tsx`、SB＝`SortBar.tsx`。

| AT | 實作 | 測試（檔） | 判定 |
|----|------|-----------|------|
| 1-1～1-5、1-E-1 | SO | `lib/domain/sorting.test.ts` AT_963_1_1…1_5、1_E_1 | PASS（S1～S4、S26 殺） |
| 2-1～2-4、2-E-1 | SH | `common/SortableHeader.test.tsx` AT_963_2_* | PASS（S5、S25 殺） |
| 3-1、3-2、3-3、3-4 | `issues/IssueTable.tsx`、`IssuesView.tsx` | `issues/IssuesView.test.tsx` AT_963_3_1～3_4 | PASS（S9、S10 殺） |
| 3-5 | `si/SiObservationsPanel.tsx` | `si/SiView.test.tsx` AT_963_3_5 | PASS／**F-02** 壞列 line 序無鑑別 |
| 3-6 | `si/SiProposalsPanel.tsx` | SiView.test.tsx AT_963_3_6 | PASS（S19 殺） |
| 3-7、3-8 | `si/SiEventsPanel.tsx` | SiView.test.tsx AT_963_3_7／3_8（合併一測，運轉表含 outcome／propIds／research 三欄獨立斷言） | PASS／**F-03** 事件 tie-break 無鑑別 |
| 3-9 | `sysadmin/BackupList.tsx` | `sysadmin/BackupView.test.tsx` AT_963_3_9 | PASS（S2、S12、S23 殺） |
| 3-10 | `research/AllowlistDialog.tsx` | `research/AllowlistDialog.test.tsx` AT_963_3_10 | PASS（S17 殺） |
| 3-11 | `research/TraceabilityTable.tsx` | `TraceabilityTable.test.tsx` AT_963_3_11 | PASS（S18 殺） |
| 3-12、3-13 | `research/EvidenceMatrixTable.tsx` | `EvidenceMatrixTable.test.tsx` AT_963_3_12／3_13 | PASS（S15 殺） |
| 3-14 | `import/HistoryPanel.tsx` | `import/HistoryPanel.test.tsx` AT_963_3_14 | PASS（S3、S13、S21、S25 殺；S22 為等價突變） |
| 3-E-1 | — | `lib/domain/sortScope.static.test.ts` | PASS |
| 3-E-2 | SiObservationsPanel | SiView.test.tsx AT_963_3_E_2 | PASS（S27 殺） |
| 4-1、4-2 | `views/ProjectsView.tsx`、SB | `views/ProjectsView.test.tsx` AT_963_4_1／4_2 | PASS／**F-01**（page=0 不可失敗） |
| 4-3、4-4 | `research/ResearchListView.tsx` | `ResearchListView.test.tsx` AT_963_4_3／4_4 | PASS（S7、S14 殺） |
| 4-E-1 | SB | `common/SortBar.test.tsx` AT_963_4_E_1 | PASS（S6、S24 殺） |
| 5-1、5-2、5-3、5-E-1、5-E-2 | `ProjectController`／`ImportController`／兩 RepositoryAdapter／兩 UseCase 列舉 | `ProjectApiIT`、`ImportFlowApiIT` AT_963_5_*（共 8 個方法） | PASS（副本 baseline rc=0；B1～B8 全殺） |
| 6-1～6-6、6-E-1 | `lib/help/readability.ts` | `lib/help/readability.test.ts` | PASS（H1～H17、H19 殺） |
| 7-1～7-5、7-E-1 | 各頁 `lib/help/*.ts`、readability `factProblems` | `lib/help/pageFacts.test.ts` | PASS（H2、H3、H5、H7、H14 殺） |
| 8-1 | — | 人讀（見 E 節） | PASS：§5 標「改預期」檔每檔 expect／it 數新 ≥ 舊（HistoryPanel 21→32／4→6、ProjectsView 46→61／9→11、ResearchListView 186→202／37→39、content.test 37→37／8→8、research-workspace 33→33、research-nav 90→90、IssuesView 253→290、BackupView 233→259、SiView 347→394、AllowlistDialog 99→108、import.mock.spec 127→129／10→10、p9-w5-ui-evidence 95→95、page-help.mock.spec 71→75）；被刪除行逐條核對皆已由改預期或更強斷言取代（SiView 三條壞列位置斷言、HistoryPanel `createdAt%2Cdesc`、Allowlist 來源序、import.mock 列序）。 |
| 8-2～8-5 | `console-sort.mock.spec.ts` | 副本 15 通過（見 D） | PASS |
| 8-6 | `page-help.mock.spec.ts` | AT_963_8_6 ✓ | PASS |
| 9 | — | V 系列 | 不評 |

## D 突變表（副本；KILLED／SURVIVED）
前端（`mut_sort*.out`）：S1 空值最前 K；S2 tieDir 忽略 K；S3 nextSort 無 defaultSort K；S4 iso 退文字 K；S5 兩鍵欄分隔符 K；S6 方向鈕兩句對調 K；S7 SortBar 換欄重設方向 K；**S8 ProjectsView filterKey 去排序 SURVIVED（F-01）**；S9 置頂列參與排序 K；S10 議題切分頁不重置 K；**S11 壞列 line 反向 SURVIVED（F-02）**；S12 備份 tieDir 拿掉 K；S13 HistoryPanel nextSort 無 defaultSort K；S14 研究列不排序 K；S15 證據表不排序 K；**S16 事件表拿掉 seq tie-break SURVIVED（F-03）**；S17 允許清單預設序拿掉 K；S18 追溯表預設序拿掉 K；S19 提案表不排序 K；S21 HistoryPanel 顯式重置分頁 K；S22 HistoryPanel filterKey 去排序 SURVIVED（等價突變：S21 的顯式重置兜底，不計）；S23 還原鈕空轉 K；S24 SortBar 空 options 仍渲染下拉 K；S25 兩鍵欄 aria-sort K；S26 collator 非 numeric K；S27 SI 觀察預設序改欄 K。S20 為空操作、不計。
FE-HELP（`mut_help*.out`）：H1 句長 60 K；H2 刪「未審批」句 K；H3 步驟次序顛倒 K；H4 放回「目前開放前兩步」K；H5 刪分流 ADMIN 確認 K；H6 PRD 去括號釋義 K；H7 匯入頁刪排序教學 K；H8 「系統」開頭放行 K；H9 purpose 上限 4 K；H10 Token 比對不設右界 K；H11 括號 ≥1 字 K；H12 說明含「API 路徑」K；H13 步驟 >40 字 K；H14 專案頁刪排序教學 K；H16 欄位下限 5 K；H17／H19 STALE 詞表少一項 K；H15／H18 找不到字串（NOAPPLY，無效）；H20 無資訊量。
後端（`mutbe.out`，副本 `gradlew cleanTest test --tests *ProjectApiIT --tests *ImportFlowApiIT`）：B1 拿掉 nulls last K（ImportFlowApiIT:646）；B2 id tie-break 改降冪 K；B3 tokenUsed 改排 createdAt K；B4 projectId 解析成 STATUS K；B5 匯入 400 訊息少 projectId K；B6 autonomyLevel 排 name K；B7 專案 400 訊息少 autonomyLevel K；B8 autonomylevel 解析成 STATUS K。8／8 殺。
E2E（`mute2e.out`；每個突變重 build 後跑 console-sort.mock.spec，`E2E_MODE=standalone`、埠 3217、各自 `--output`）：E1 專案請求 sort 寫死 K（8-2）；E2 置頂列參與排序 K（8-3）；E3 還原鈕空轉 K（8-5）；E4 研究列排序鍵寫死編號 K（8-4）；E5 說明放回「目前開放前兩步」K（8-4）；E6 方向鈕 aria-label 寫死 K（8-2）。6／6 殺。

## E 接縫
- 前端送出的 `sort` ⇄ 後端白名單：專案 createdAt／name／status／updatedAt／autonomyLevel、匯入 createdAt／sourceFileName／status／projectId／aiModel／tokenUsed 與兩支 Controller 的解析與 400 訊息逐字一致（B4、B5、B7、B8 殺，AT_963_3_14 與 AT_963_4_1 解碼後比對請求）。
- `<th>` textContent 鎖（議題八欄、備份十欄、追溯表、允許清單八欄、證據表七欄）全綠；`aria-sort` 與 `nextSort(defaultSort)` 首次點預設欄即反向（S3、S13 殺）。
- 議題四分頁預設序＝R-IC-33（`lib/domain/issues.ts` 零 diff、AT_963_3_1／3_2 綠）；根層 `tools/**` 零 diff。
- SI 壞列落點（有效列之後）已測、壞列內部序為 F-02；備份 tieDir 降冪（S2、S12 殺）；說明文案 `sourceFiles` 出處鎖與三道登記鎖（registry.test.ts）、`lint.ts` 疊加於 readability 皆在 111 檔全綠內；`research.ts` 說明無「目前開放前兩步」（H4 殺）。

## F 文案人讀（projects／research／research-workspace）
- projects：10 步可走完一遍（新建或匯入→目標→任務→審批→執行→監控），按鈕名（新建專案、查看、執行、監控、已刪除、復原）與 ProjectCard／ProjectsView 實況一致；唯讀、已刪除可見性條件正確。僅 F-04（第 6 步「按不了」）P3。語氣國高中可讀。
- research：五步名稱、研究命題必填且最多 500 字（ResearchListView:174）、封存 30 天內可復原（:400/:404）、「繼續」連結、「重試初始化」皆與畫面一致。
- research-workspace：五步依序、ADMIN 核准凍結／確認分流、「退回修改」、「對帳」鈕（ResearchWorkspaceView:168）皆對得上；第 10 步說「頁首的『對帳』」，鈕實在工作區頁首列，OK。欄位表很長（逾 100 列）但屬既有範圍，P4 不立案。

## G 裁決偏離與勘誤核實
- 無新增未登記偏離。實作依 D-UX-18（議題預設序不改、四分頁 aria-sort 全 none）、D-UX-19（專案／匯入預設 createdAt,asc）、D-UX-20（允許清單以主機為識別欄）、D-UX-21（steps 2～10，content.test／research-workspace.test／research-nav.test 與 AT_PH_03_5 標題界線數字同改，即 E-3）。
- 核實 E-2、E-3、E-4、E-5、E-6、E-7、E-8、E-9、E-10、E-11：皆與工作樹一致（E-11：research-docker.stack.spec 與 research-studio-perf.mock.spec 在 diff 中確實未改）。補列候選：本審查發現 `SortBar` 換欄位時沿用現行方向（`{key,dir:state.dir}`，S7 殺）而 W-UX5 未明寫此點，建議 RELEASE_READY 勘誤補一句。

## H 誠實劃界
- E2E 突變只在 console-sort.mock.spec 上重建驗證（每個突變一次 `npm run build`），page-help.mock.spec／import.mock.spec／issues.mock.spec／sysadmin-backup.mock.spec／projects.mock.spec 六支基準跑只做了 console-sort＋page-help 兩支（15 通過），其餘四支未重跑，沿主控回報 29 通過［他包回報］。
- `p9-w5-ui-evidence.spec.ts`、各 `*.stack.spec.ts` 需真後端或 Docker 全棧，NOT-EVALUABLE（V2 範圍）。
- AT-963-9（V1～V5）、Docker 真機未評。前端副本 node_modules 為複製、非 junction。
- 未做的審查面：後端 JaCoCo／checkstyle、`gradlew clean build` 全量（沿主控 4m54s）；`openapi-p3-6.yaml`／API_Contract 文件條文（V4，主控勘誤批次）。

## I 二審（修復 commit 1c7cdd8a；僅動 SiView.test.tsx、ProjectsView.test.tsx、lib/help/projects.ts）
**判定：PASS（P1 0／P2 0／P3 0）。**
1. 存活突變在 HEAD 副本重放（junction 掛 node_modules）：S8（ProjectsView filterKey 去排序）KILLED rc=1，失敗＝`AT_963_4_1 多頁時：已在第 2 頁，改排序欄位與按方向鈕，下一個請求都帶 page=0`；S11（壞列 line 反向）KILLED rc=1，失敗＝`AT_963_3_5 觀察表…壞列恆在有效列之後…`；S16（拿掉事件表 seq tie-break）KILLED rc=1，失敗＝`AT_963_3_7／3_8 事件表與運轉表…`。F-01～F-03 關閉。
2. F-04 新句「審批完成後按卡片上的「執行」進入執行頁，無法開始時先檢查有沒有審批。」：單句、約 34 字（≤40）、含動作詞「按」「進入」「檢查」；與 ProjectCard 實況一致（卡片「執行」為連結，開始動作在執行頁）；P6 次序（審批→執行→監控）仍成立，pageFacts 綠。關閉。
3. 未退化：真實工作樹 `npx vitest run components/domain/si components/domain/views lib/help lib/nav components/domain/common` rc=0，26 檔 290 通過；`npx tsc --noEmit` rc=0。涵蓋 AT_963_3_5～3_8、3_E_2、4_1、4_2、4_E_1、6_*、7_* 皆綠。`OBS-SI-` 字面拆分只動測試碼字串組合，行為不變。
4. 範圍：`git diff --name-only fcb8959c..HEAD` 僅上述三檔。副本已刪除，工作樹乾淨。
未重跑：後端與 Playwright（本輪修復未觸及）。
