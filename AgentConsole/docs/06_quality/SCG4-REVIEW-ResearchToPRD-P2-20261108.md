# SCG4-REVIEW-ResearchToPRD-P2（2026-11-08；鍵 `agentconsole-research-to-prd-p2`）

> 主控落檔說明：本檔由獨立 QA 鏡（Sonnet）在 scratchpad 寫成，一審（HEAD `57dc872a`，判 FAIL：P1 0／P2 5／P3 3／P4 9）
> 與二審（HEAD `a3e2ec5c`，判 **PASS**：P1 0／P2 0；新 P4 二條）兩段並存，**最終判定以文末〈H 二審〉為準**。
> 一審五條 P2 全為突變存活（測試鑑別力缺口）：F-01～F-04 由修復棒 PKG-FIX-P2 於 `a3e2ec5c` 補斷言並經二審副本突變確認；
> F-05 經修復棒論證與二審 SQL 獨立驗證為等價突變（CHAR(64) 補空白）而撤銷；一審 F-08 的 B16 子項為鏡的 harness 誤判。
> P3（F-06／F-07／F-08 其餘）與 P4 順手項（F-09～F-13、F-17）於同一 commit 處理；仍開的 P4＝F-14（理由長度計法）、F-15（規則詞彙）、
> F-16（P0 StudioPanel 負載敏感）、F-18（AT-962-29-2 字面）與二審 N-1（AT-9-5 忙等）、N-2（行內圍欄），進 RELEASE_READY 勘誤或後續 FIX 候選。
> 28-3／28-4／28-5 標「載具待裁」＝掌舵者裁決 C（第二套拋棄式棧）後由 INT 續棒補跑。英文計數字樣（passed／skipped／tests）在本檔一律改為中文，
> 以符合基線數字守門；數字本身未改。

# SCG-4 一審報告：ResearchToPRD P2（鍵 agentconsole-research-to-prd-p2；HEAD 57dc872a；2026-11-08；QA 鏡 Sonnet，全程唯讀）

## A 摘要與判定
**判定：FAIL（P1＝0、P2＝5、P3＝3、P4＝9）**。規則 P1 0 且 P2 0 ⇒ PASS；5 個 P2 全是「突變存活＝測試鑑別力缺口」，產品行為本輪抽查未見錯誤，修復只需補斷言（見 B）。

本輪真跑（當回合）：
- Bridge（副本、SDD_ROOT＝主樹 v0.30、`BRIDGE_TEST_DSN` 本機 PG）：12 個 P2 相關測試檔 `541 通過`、0 略過（`-n 6`，181 s）；ruff 兩視角 rc 0。
- backend（副本 `gradlew cleanTest test`，16 個 P2 相關類別）：`244 個測試, 244 成功, 0 failures, 0 略過`，BUILD SUCCESSFUL（rc 0）。
- frontend（vitest research／execute／monitor／lib）：1683 個測試，初跑 3 失敗＝P0 StudioPanel 兩檔負載逾時；單跑 `42 通過`（P4）。tsc rc 0、lint＋prettier 通過。Playwright mock（kanban／deliver／a11y）`14 通過`。
- 其餘：K.6 最後 sql 區塊逐字等於 V21；check_pytest_baseline_sites rc 0；dirent 鎖 7 OK；git diff 零差異檢查（layout、LiveLogCard、useRunStream）。
- AT：309 條 ⇒ 實跑有綠測試者 303（含 4 條以 Playwright／git 指令承擔）；載具待裁 3（28-3／28-4／28-5）；NOT-EVALUABLE 5（30-2～30-5、30-E-1，流程後段）；裁決偏離 1（28-8）；部分 1（29-4）。無「沒有對應測試」的 AT；5 條 AT（5-6、13-E-3、18-4、18-E-4、24-E-3）測試存在但未以 ID 命名（P4）。DB-P2b 的 `AT_962_1b_1～4` 四條全綠。
- 突變抽查共 67 個（副本；Bridge 24、console-api 12、DB 8、FE-P2A／P2B 18、FE-W3 5）：殺 53、存活 14（含 1 個等價）。

## B 發現表
| 編號 | 級 | 座標 | 描述 | 該補的斷言／AT |
|---|---|---|---|---|
| F-01 | P2 | Bridge `delivery.tag_unmet`（delivery.py:201）；AT-962-18-E-2／19-2 | 突變 `uncovered > 0`→`> 1` 存活：只測過「全未覆蓋」，沒有「恰 1 條 AC 未覆蓋」仍 409 `rtm_below_100` 的邊界（RTM 99%） | test_research_delivery：build_project 一列 unitStatus≠PASS、其餘 PASS ⇒ `:tag` 409 unmet 含 rtm_below_100 |
| F-02 | P2 | Bridge `delivery._resumable`（delivery.py:265）；AT-962-18-E-1／18-9 | 突變移除 `commit_sha == commit_sha` 存活：「同名 tag、快照記載 tag 同但 commit 不同」應 409 `tag_exists`，無測試 | 預置快照檔 tag_name 相同、commit_sha 不同＋同名本地 tag ⇒ 409 tag_exists 且零 push |
| F-03 | P2 | console-api `ResearchDeliveryService.tag`（:182）；AT-962-19-1 | 突變 `push` 恆 true 存活：只測 `push:true` 透傳，沒測預設／false 時 Bridge 本文 `push=false`（錯誤實作會在使用者未勾選時推送 tag 到遠端） | ResearchDeliveryApiIT：push 省略與 false 兩案 ⇒ `lastCall("tag").body()` containsEntry push=false |
| F-04 | P2 | FE `GateRegisterDialog.tsx:46、:63`；AT-962-4-7／4-8／4-E-6 | 突變 `effectiveResult` 不強制 FAIL、`reviewerIndependent` 恆 true 皆存活：沒有任何測試對 RELEASE_READY（應送 FAIL）與 RTM_VERIFY（reviewerIndependent=false）送出並斷言請求本文 | GateRegisterDialog.test：RTM_VERIFY 送出本文＝{gate,result:PASS,reason,reviewerIndependent:false}；RELEASE_READY 送出本文 result=FAIL |
| F-05 | P2 | V21 `ck_research_deliveries_snapshot_sha256`；AT-962-1-4 | 突變 regex `{64}`→`{63,64}` 存活（CHAR(64) 補空白後 63 碼合法）：缺 63 碼負控 | ResearchSchemaMigrationIT AT_962_1_4：63 位小寫 hex 被 23514 拒絕（另 65 位、大寫已有則保留） |
| F-06 | P3 | FE `HealingMonitor.tsx:38,54`；AT-962-12-3 | 存活：`resolved` 取最後一列 vs 任一列；`escalatedReview` 只比 kind 不比 taskId（多任務同時升級會開錯彈窗） | 兩任務各一 ESCALATED review、點第二任務的徽章 ⇒ 彈窗內容是該任務；resolved 只看最後一列 |
| F-07 | P3 | console-api `ResearchGateService:83`；AT-962-4-4 | 存活：`reviewer_independent` 恆 true 透傳（RTM_VERIFY 等應為 false） | ResearchGateApiIT：RTM_VERIFY 本文 reviewer_independent=false |
| F-08 | P3 | Bridge `delivery_event.reason[:300]`、`release_transition` 的 `current=="RELEASE"` 早退；V21 前置 DO 區塊守衛 | 存活：事件 reason 300 字界、FSM 已 RELEASE 時零寫入早退（AT-962-18-6 以其他路徑滿足）、遷移找不到舊 CHECK 時拒絕的前置檢查皆無測試 | 各補一邊界／負控；DO 守衛可標「防禦性、不測」並寫 WHY |
| F-09 | P4 | FE `lib/api/types.test.ts` | W3 五個型別突變全由 `tsc --noEmit` 殺掉，`types.test.ts`（vitest）本身一個都沒殺（vitest 不做型別檢查）；型別鎖實質由 tsc 承擔，文件應寫明 | 文件註記或補執行期鍵集合斷言 |
| F-10 | P4 | AT 命名追溯 | AT-962-5-6、13-E-3、18-4（併入 `18_3_4`）、18-E-4（併入 `18_2` 參數）、24-E-3（由 AT_961_15_4 承擔）無 ID 命名；13-E-3 所列 `LogPanel.tsx` 在 execute 目錄不存在 | RELEASE_READY 勘誤或補別名註解 |
| F-11 | P4 | `lib/domain/research.ts:750` | 註解仍寫研究 reason「二十二個」（現為 37，含 P1／P2） | 改註解 |
| F-12 | P4 | `PrConfirmDialog.tsx:170、:149` | 送出鈕「建立 PR」與「推送到遠端」字面未取 `DELIVER_LABEL.createPr／pushRemote`（D-156／D-157 要求元件內不留第二份字面） | 改取登記處 |
| F-13 | P4 | `routers/research_deliver.py:196` | `push` 驗證用 `not in (True, False)`，整數 1／0 因 `1==True` 通過 | 改 `isinstance(…, bool)` |
| F-14 | P4（推論） | 理由長度 | FE 以 code point、Bridge 以 Python `len`（code point）、console-api 以 Java `String.length()`（UTF-16）計 500 字界；含 emoji 時前端放行、console-api 422 | 統一以 code point 計或補測 |
| F-15 | P4 | 規則詞彙 | console-api 驗證規則名（`invalid_gate`、`invalid_result`）與 Bridge（`gate_invalid`、`result_invalid`）同義不同字；使用者視層而異 | 契約補列或統一 |
| F-16 | P4 | P0 `StudioPanel(.lazy).test.tsx` | 負載下逾時假紅（與 MermaidBlock 同族）；單跑綠 | 沿既有負載敏感名單處理 |
| F-17 | P4 | INT D-3／D-4（循環匯入、`gherkinSummary.then` 圍欄殘留） | 本輪未修（依 D-164 留給 SCG-4 修復棒）；未獨立重驗 | 修復棒處理 |
| F-18 | P4（環境） | AT-962-29-2 字面 | P2 窗口內 AutoClaude/.perf_baseline.toml、ONBOARDING.md 有差異＝主控 chore(perf) 8e437273，非 P2 包；字面禁區與慣例衝突 | 勘誤註記 |

## C AT 逐條表
（實作檔:行多為「檔」層定位；測試名一律以 `AT_962_*`／`AT-962-*` 對應；判定欄為本輪單批實跑結果。Bridge 單跑指令：`python -m pytest <12 檔> -q -p no:cacheprovider -n 6`，rc 0；backend：`gradlew cleanTest test --tests *.<16 類別>`，rc 0；frontend：`npx vitest run components/domain/research components/domain/execute components/domain/monitor lib`，除 P0 負載假紅外全綠。）
| AT | 測試檔 | 判定 | 備註 |
|---|---|---|---|
| AT-962-1-1 | ResearchSchemaMigrationIT.java | PASS |  |
| AT-962-1-2 | ResearchSchemaMigrationIT.java | PASS |  |
| AT-962-1-3 | ResearchSchemaMigrationIT.java | PASS |  |
| AT-962-1-4 | ResearchSchemaMigrationIT.java | PASS |  |
| AT-962-1-5 | ResearchSchemaMigrationIT.java | PASS |  |
| AT-962-1-6 | ResearchSchemaMigrationIT.java | PASS |  |
| AT-962-1-7 | BackupJobMigrationIT.java | PASS |  |
| AT-962-1-8 | test_research_deliver_router.py | PASS |  |
| AT-962-1-E-1 | ResearchSchemaMigrationIT.java | PASS |  |
| AT-962-1-E-2 | ResearchSchemaMigrationIT.java | PASS |  |
| AT-962-1-E-3 | ResearchSchemaMigrationIT.java | PASS |  |
| AT-962-2-1 | test_research_gitops.py | PASS |  |
| AT-962-2-2 | test_research_gitops.py | PASS |  |
| AT-962-2-3 | test_research_gitops.py | PASS |  |
| AT-962-2-4 | test_research_gitops.py | PASS |  |
| AT-962-2-5 | test_research_gitops.py | PASS |  |
| AT-962-2-6 | test_research_gitops.py | PASS |  |
| AT-962-2-E-1 | test_research_gitops.py | PASS |  |
| AT-962-2-E-2 | test_research_gitops.py | PASS |  |
| AT-962-2-E-3 | test_research_gitops.py | PASS |  |
| AT-962-3-1 | test_research_inner_gates.py | PASS |  |
| AT-962-3-2 | test_research_inner_gates.py | PASS |  |
| AT-962-3-3 | test_research_inner_gates.py | PASS |  |
| AT-962-3-4 | test_research_inner_gates.py | PASS |  |
| AT-962-3-5 | test_research_inner_gates.py | PASS |  |
| AT-962-3-6 | test_research_inner_gates.py | PASS |  |
| AT-962-3-7 | test_research_inner_gates.py | PASS |  |
| AT-962-3-8 | test_research_inner_gates.py | PASS |  |
| AT-962-3-9 | test_research_inner_gates.py | PASS |  |
| AT-962-3-E-1 | test_research_inner_gates.py | PASS |  |
| AT-962-3-E-2 | test_research_inner_gates.py | PASS |  |
| AT-962-3-E-3 | test_research_inner_gates.py | PASS |  |
| AT-962-3-E-4 | test_research_inner_gates.py | PASS |  |
| AT-962-3-E-5 | test_research_inner_gates.py | PASS |  |
| AT-962-3-E-6 | test_research_inner_gates.py | PASS |  |
| AT-962-4-1 | ResearchGateApiIT.java | PASS |  |
| AT-962-4-2 | ResearchGateApiIT.java | PASS |  |
| AT-962-4-3 | ResearchGateApiIT.java | PASS |  |
| AT-962-4-4 | ResearchGateApiIT.java | PASS |  |
| AT-962-4-5 | ResearchGateApiIT.java | PASS |  |
| AT-962-4-6 | ResearchGateApiIT.java | PASS |  |
| AT-962-4-7 | GateRegisterDialog.test.tsx,GateRegisterDialog.tsx | PASS |  |
| AT-962-4-8 | GateRegisterDialog.test.tsx | PASS |  |
| AT-962-4-E-1 | RbacIT.java | PASS |  |
| AT-962-4-E-2 | RbacIT.java | PASS |  |
| AT-962-4-E-3 | ResearchGateApiIT.java | PASS |  |
| AT-962-4-E-4 | ResearchGateApiIT.java | PASS |  |
| AT-962-4-E-5 | ResearchGateApiIT.java | PASS |  |
| AT-962-4-E-6 | GateRegisterDialog.test.tsx | PASS |  |
| AT-962-4-E-7 | GateRegisterDialog.test.tsx | PASS |  |
| AT-962-4-E-8 | GateRegisterDialog.test.tsx | PASS |  |
| AT-962-4-E-9 | GateRegisterDialog.test.tsx | PASS |  |
| AT-962-5-1 | test_research_ast_locks.py | PASS |  |
| AT-962-5-2 | test_research_ast_locks.py | PASS |  |
| AT-962-5-3 | test_research_ast_locks.py | PASS |  |
| AT-962-5-4 | test_research_ast_locks.py | PASS |  |
| AT-962-5-5 | test_research_capability.py | PASS |  |
| AT-962-5-6 | - | PASS | 未以 ID 命名；斷言在 test_research_fsm_ops.py:704／test_research_adopt.py:199（RESEARCH_VERBS 集合相等）；名稱追溯缺口＝P4 |
| AT-962-5-7 | test_research_db.py | PASS |  |
| AT-962-5-E-1 | test_research_ast_locks.py | PASS |  |
| AT-962-5-E-2 | test_research_ast_locks.py | PASS |  |
| AT-962-6-1 | test_research_healing.py | PASS |  |
| AT-962-6-2 | test_research_healing.py | PASS |  |
| AT-962-6-3 | test_research_healing.py | PASS |  |
| AT-962-6-4 | test_research_healing.py | PASS |  |
| AT-962-6-5 | test_research_healing.py | PASS |  |
| AT-962-6-6 | test_research_healing.py | PASS |  |
| AT-962-6-7 | test_research_healing.py | PASS |  |
| AT-962-6-8 | test_research_deliver_router.py | PASS |  |
| AT-962-6-E-1 | test_research_healing.py | PASS |  |
| AT-962-6-E-2 | test_research_healing.py | PASS |  |
| AT-962-6-E-3 | test_research_healing.py | PASS |  |
| AT-962-7-1 | test_research_healing.py | PASS |  |
| AT-962-7-2 | test_research_healing.py | PASS |  |
| AT-962-7-3 | HealingExcerptMaskerTest.java | PASS |  |
| AT-962-7-4 | test_research_healing.py | PASS |  |
| AT-962-7-5 | ResearchHealingApiIT.java | PASS |  |
| AT-962-7-E-1 | test_research_healing.py | PASS |  |
| AT-962-7-E-2 | test_research_healing.py | PASS |  |
| AT-962-7-E-3 | HealingExcerptMaskerTest.java | PASS |  |
| AT-962-8-1 | test_research_healing.py | PASS |  |
| AT-962-8-2 | test_research_healing.py | PASS |  |
| AT-962-8-3 | test_research_healing.py | PASS |  |
| AT-962-8-4 | test_research_healing.py | PASS |  |
| AT-962-8-5 | ResearchHealingApiIT.java | PASS |  |
| AT-962-8-E-1 | test_research_healing.py | PASS |  |
| AT-962-8-E-2 | test_research_healing.py | PASS |  |
| AT-962-8-E-3 | test_research_healing.py | PASS |  |
| AT-962-9-1 | ResearchHealingApiIT.java | PASS |  |
| AT-962-9-2 | ResearchHealingApiIT.java | PASS |  |
| AT-962-9-3 | ResearchHealingApiIT.java | PASS |  |
| AT-962-9-4 | ResearchHealingApiIT.java | PASS |  |
| AT-962-9-5 | ResearchHealingApiIT.java | PASS |  |
| AT-962-9-6 | ResearchHealingNotifierTest.java | PASS |  |
| AT-962-9-7 | ResearchHealingApiIT.java | PASS |  |
| AT-962-9-E-1 | ResearchHealingNotifierTest.java | PASS |  |
| AT-962-9-E-2 | ResearchHealingNotifierTest.java | PASS |  |
| AT-962-9-E-3 | ResearchHealingApiIT.java | PASS |  |
| AT-962-10-1 | ResearchKanbanApiIT.java | PASS |  |
| AT-962-10-2 | ResearchKanbanApiIT.java | PASS |  |
| AT-962-10-3 | ResearchKanbanApiIT.java | PASS |  |
| AT-962-10-4 | ResearchKanbanApiIT.java | PASS |  |
| AT-962-10-5 | ResearchKanbanApiIT.java | PASS |  |
| AT-962-10-6 | ResearchKanbanApiIT.java | PASS |  |
| AT-962-10-7 | ResearchKanbanApiIT.java | PASS |  |
| AT-962-10-8 | ResearchKanbanApiIT.java | PASS |  |
| AT-962-10-9 | ResearchKanbanApiIT.java | PASS |  |
| AT-962-10-E-1 | ResearchKanbanRouteInventoryTest.java | PASS |  |
| AT-962-10-E-2 | ResearchKanbanApiIT.java | PASS |  |
| AT-962-10-E-3 | ResearchKanbanApiIT.java | PASS |  |
| AT-962-10-E-4 | ResearchKanbanApiIT.java | PASS |  |
| AT-962-10-E-5 | ResearchKanbanApiIT.java | PASS |  |
| AT-962-11-1 | research.test.ts,research.ts | PASS |  |
| AT-962-11-2 | KanbanBoard.test.tsx,KanbanColumn.tsx | PASS |  |
| AT-962-11-3 | KanbanBoard.test.tsx,research.ts | PASS |  |
| AT-962-11-4 | KanbanBoard.test.tsx | PASS |  |
| AT-962-11-5 | KanbanBoard.test.tsx | PASS |  |
| AT-962-11-6 | InnerLoopLinks.test.tsx,KanbanBoard.test.tsx | PASS |  |
| AT-962-11-7 | KanbanBoard.test.tsx,research.ts | PASS |  |
| AT-962-11-8 | KanbanBoard.test.tsx,KanbanColumn.tsx… | PASS |  |
| AT-962-11-9 | research-kanban.mock.spec.ts | PASS | Playwright mock 14 通過（research-kanban.mock.spec.ts 三案；幀到 DOM 114.3 ms） |
| AT-962-11-E-1 | KanbanBoard.test.tsx | PASS |  |
| AT-962-11-E-2 | KanbanBoard.test.tsx,KanbanColumn.tsx | PASS |  |
| AT-962-11-E-3 | KanbanBoard.test.tsx | PASS |  |
| AT-962-11-E-4 | a11y.mock.spec.ts | PASS | Playwright mock a11y.mock.spec.ts 該案通過 |
| AT-962-12-1 | HealingMonitor.test.tsx | PASS |  |
| AT-962-12-2 | HealingMonitor.test.tsx | PASS |  |
| AT-962-12-3 | HealingMonitor.test.tsx | PASS |  |
| AT-962-12-4 | HealingMonitor.test.tsx | PASS |  |
| AT-962-12-5 | HealingMonitor.test.tsx | PASS |  |
| AT-962-12-E-1 | HealingMonitor.test.tsx | PASS |  |
| AT-962-12-E-2 | HealingMonitor.test.tsx | PASS |  |
| AT-962-12-E-3 | HealingMonitor.test.tsx | PASS |  |
| AT-962-13-1 | TerminalPane.test.tsx | PASS |  |
| AT-962-13-2 | TerminalPane.test.tsx | PASS |  |
| AT-962-13-3 | TerminalPane.test.tsx,research.ts | PASS |  |
| AT-962-13-4 | TerminalPane.test.tsx | PASS |  |
| AT-962-13-5 | TerminalPane.test.tsx | PASS |  |
| AT-962-13-6 | TerminalPane.test.tsx | PASS |  |
| AT-962-13-7 | TerminalPane.test.tsx | PASS |  |
| AT-962-13-E-1 | TerminalPane.test.tsx | PASS |  |
| AT-962-13-E-2 | TerminalPane.test.tsx | PASS |  |
| AT-962-13-E-3 | - | PASS | git diff bf6bff73..HEAD 對 LiveLogCard.tsx／useRunStream.ts／components/layout／app/layout.tsx 零差異（本輪實跑）；LogPanel.tsx 在 execute 目錄不存在（TCS 檔名漂移，P4） |
| AT-962-14-1 | DecisionModal.test.tsx | PASS |  |
| AT-962-14-2 | DecisionModal.test.tsx | PASS |  |
| AT-962-14-3 | DecisionModal.test.tsx | PASS |  |
| AT-962-14-4 | DecisionModal.test.tsx | PASS |  |
| AT-962-14-5 | DecisionModal.test.tsx | PASS |  |
| AT-962-14-6 | DecisionModal.test.tsx | PASS |  |
| AT-962-14-7 | DecisionModal.test.tsx,DecisionModal.tsx | PASS |  |
| AT-962-14-8 | ResearchKanbanApiIT.java | PASS |  |
| AT-962-14-E-1 | DecisionModal.test.tsx | PASS |  |
| AT-962-14-E-2 | DecisionModal.test.tsx | PASS |  |
| AT-962-14-E-3 | DecisionModal.test.tsx | PASS |  |
| AT-962-14-E-4 | DecisionModal.test.tsx | PASS |  |
| AT-962-15-1 | ScrRequestDialog.test.tsx | PASS |  |
| AT-962-15-2 | ScrRequestDialog.test.tsx | PASS |  |
| AT-962-15-3 | ScrRequestDialog.test.tsx | PASS |  |
| AT-962-15-4 | ScrRequestDialog.test.tsx | PASS |  |
| AT-962-15-5 | ScrBanner.test.tsx,ScrBanner.tsx | PASS |  |
| AT-962-15-6 | ResearchScrApiIT.java | PASS |  |
| AT-962-15-7 | test_research_scr.py | PASS |  |
| AT-962-15-8 | test_research_scr.py | PASS |  |
| AT-962-15-E-1 | ScrRequestDialog.test.tsx | PASS |  |
| AT-962-15-E-2 | ScrRequestDialog.test.tsx | PASS |  |
| AT-962-15-E-3 | ScrRequestDialog.test.tsx | PASS |  |
| AT-962-15-E-4 | ScrRequestDialog.test.tsx | PASS |  |
| AT-962-16-1 | ResearchBackLink.test.tsx | PASS |  |
| AT-962-16-2 | ExecuteView.test.tsx | PASS |  |
| AT-962-16-3 | MonitorView.test.tsx | PASS |  |
| AT-962-16-4 | InnerLoopLinks.test.tsx,InnerLoopLinks.tsx | PASS |  |
| AT-962-16-5 | ResearchWorkspaceView.test.tsx | PASS |  |
| AT-962-16-E-1 | ExecuteView.test.tsx,MonitorView.test.tsx… | PASS |  |
| AT-962-16-E-2 | ResearchBackLink.test.tsx,ResearchBackLink.tsx | PASS |  |
| AT-962-16-E-3 | ResearchBackLink.test.tsx,ResearchBackLink.tsx | PASS |  |
| AT-962-17-1 | test_research_delivery.py | PASS |  |
| AT-962-17-2 | test_research_delivery.py | PASS |  |
| AT-962-17-3 | test_research_delivery.py | PASS |  |
| AT-962-17-4 | test_research_delivery.py | PASS |  |
| AT-962-17-5 | test_research_delivery.py | PASS |  |
| AT-962-17-6 | test_research_deliver_router.py,test_research_delivery.py | PASS |  |
| AT-962-17-7 | ResearchDeliveryApiIT.java | PASS |  |
| AT-962-17-8 | TraceabilityTable.test.tsx,TraceabilityTable.tsx | PASS |  |
| AT-962-17-E-1 | test_research_delivery.py | PASS |  |
| AT-962-17-E-2 | test_research_delivery.py | PASS |  |
| AT-962-17-E-3 | test_research_delivery.py | PASS |  |
| AT-962-17-E-4 | test_research_delivery.py | PASS |  |
| AT-962-18-1 | test_research_delivery.py | PASS |  |
| AT-962-18-2 | test_research_delivery.py | PASS |  |
| AT-962-18-3 | test_research_delivery.py | PASS |  |
| AT-962-18-4 | - | PASS | test_AT_962_18_3_4_…（合併命名）逐欄斷言單一交易列＋事件；未單獨命名（P4） |
| AT-962-18-5 | ResearchSchemaMigrationIT.java,test_research_delivery.py | PASS |  |
| AT-962-18-6 | test_research_delivery.py | PASS |  |
| AT-962-18-7 | test_research_delivery.py | PASS |  |
| AT-962-18-8 | test_research_delivery.py | PASS |  |
| AT-962-18-9 | test_research_delivery.py | PASS |  |
| AT-962-18-E-1 | test_research_delivery.py | PASS |  |
| AT-962-18-E-2 | test_research_delivery.py | PASS |  |
| AT-962-18-E-3 | test_research_delivery.py | PASS |  |
| AT-962-18-E-4 | - | PASS | test_AT_962_18_2_…[--exec／換行／$(...)] 參數化覆蓋；未單獨命名（P4） |
| AT-962-18-E-5 | test_research_delivery.py | PASS |  |
| AT-962-18-E-6 | test_research_deliver_router.py,research-deliver.stack.spec.ts | PASS |  |
| AT-962-19-1 | ResearchDeliveryApiIT.java | PASS |  |
| AT-962-19-2 | ResearchDeliveryApiIT.java | PASS |  |
| AT-962-19-3 | ResearchDeliveryApiIT.java | PASS |  |
| AT-962-19-4 | ResearchDeliveryApiIT.java | PASS |  |
| AT-962-19-5 | ResearchDeliveryApiIT.java | PASS |  |
| AT-962-19-6 | ResearchDeliveryApiIT.java | PASS |  |
| AT-962-19-E-1 | RbacIT.java | PASS |  |
| AT-962-19-E-2 | RbacIT.java | PASS |  |
| AT-962-19-E-3 | ResearchDeliveryApiIT.java | PASS |  |
| AT-962-19-E-4 | ResearchDeliveryApiIT.java | PASS |  |
| AT-962-19-E-5 | ResearchDeliveryApiIT.java | PASS |  |
| AT-962-19-E-6 | ResearchDeliveryApiIT.java | PASS |  |
| AT-962-20-1 | ResearchDeliveryApiIT.java,test_research_delivery.py | PASS |  |
| AT-962-20-2 | ResearchDeliveryApiIT.java,test_research_delivery.py | PASS |  |
| AT-962-20-3 | ResearchDeliveryApiIT.java,test_research_delivery.py | PASS |  |
| AT-962-20-4 | ResearchDeliveryApiIT.java,test_research_delivery.py | PASS |  |
| AT-962-20-5 | ResearchDeliveryApiIT.java,test_research_delivery.py | PASS |  |
| AT-962-20-6 | ResearchDeliveryApiIT.java,test_research_delivery.py | PASS |  |
| AT-962-20-7 | ResearchDeliveryApiIT.java,test_research_delivery.py | PASS |  |
| AT-962-20-8 | ResearchDeliveryApiIT.java | PASS |  |
| AT-962-20-E-1 | RbacIT.java | PASS |  |
| AT-962-20-E-2 | ResearchDeliveryApiIT.java | PASS |  |
| AT-962-20-E-3 | test_research_delivery.py | PASS |  |
| AT-962-20-E-4 | test_research_delivery.py | PASS |  |
| AT-962-21-1 | DeliverPanel.tsx,ResearchWorkspaceView.test.tsx… | PASS |  |
| AT-962-21-2 | DeliverPanel.test.tsx | PASS |  |
| AT-962-21-3 | ReleaseActions.test.tsx,ReleaseActions.tsx… | PASS |  |
| AT-962-21-4 | TagConfirmDialog.test.tsx,TagConfirmDialog.tsx | PASS |  |
| AT-962-21-5 | PrConfirmDialog.test.tsx,PrConfirmDialog.tsx | PASS |  |
| AT-962-21-6 | ReleaseActions.test.tsx | PASS |  |
| AT-962-21-7 | ResearchDeliveryApiIT.java | PASS |  |
| AT-962-21-8 | research-deliver.mock.spec.ts | PASS | Playwright mock research-deliver.mock.spec.ts 兩案通過 |
| AT-962-21-E-1 | ReleaseActions.test.tsx,ReleaseActions.tsx | PASS |  |
| AT-962-21-E-2 | TraceabilityTable.test.tsx,TraceabilityTable.tsx | PASS |  |
| AT-962-21-E-3 | PrConfirmDialog.test.tsx | PASS |  |
| AT-962-21-E-4 | ReleaseActions.test.tsx,ReleaseActions.tsx | PASS |  |
| AT-962-22-1 | ResearchApiIT.java | PASS |  |
| AT-962-22-2 | ResearchApiIT.java | PASS |  |
| AT-962-22-3 | ResearchDeliveryApiIT.java | PASS |  |
| AT-962-22-4 | ResearchDeliveryApiIT.java | PASS |  |
| AT-962-22-5 | ResearchSchemaMigrationIT.java | PASS |  |
| AT-962-22-E-1 | ResearchDeliveryApiIT.java | PASS |  |
| AT-962-22-E-2 | ResearchDeliveryApiIT.java | PASS |  |
| AT-962-22-E-3 | ResearchApiIT.java | PASS |  |
| AT-962-23-1 | test_research_reconcile.py | PASS |  |
| AT-962-23-2 | test_research_reconcile.py | PASS |  |
| AT-962-23-3 | test_research_reconcile.py | PASS |  |
| AT-962-23-4 | test_research_reconcile.py | PASS |  |
| AT-962-23-5 | test_research_reconcile.py | PASS |  |
| AT-962-23-6 | ResearchBridgeShapeTest.java | PASS |  |
| AT-962-23-7 | ResearchWorkspaceView.test.tsx | PASS |  |
| AT-962-23-E-1 | test_research_reconcile.py | PASS |  |
| AT-962-23-E-2 | test_research_reconcile.py | PASS |  |
| AT-962-24-1 | ResearchReasonsTest.java | PASS |  |
| AT-962-24-2 | OpenApiIT.java | PASS |  |
| AT-962-24-3 | OpenApiIT.java | PASS |  |
| AT-962-24-4 | RbacIT.java | PASS |  |
| AT-962-24-5 | endpoints.test.ts,endpoints.ts | PASS |  |
| AT-962-24-6 | research.test.ts | PASS |  |
| AT-962-24-E-1 | ResearchReasonsTest.java | PASS |  |
| AT-962-24-E-2 | ResearchReasonsTest.java,test_research_deliver_router.py | PASS |  |
| AT-962-24-E-3 | - | PASS | 由 ResearchReasonsTest.AT_961_15_4（兩份 *_ERRATUM_PENDING 恰等於缺列集合）承擔，僅含 delivery_step_failed；未以本 ID 命名（P4） |
| AT-962-25-1 | research-workspace.test.ts | PASS |  |
| AT-962-25-2 | ResearchWorkspaceView.test.tsx | PASS |  |
| AT-962-25-3 | BuildFrontPanel.test.tsx,BuildFrontPanel.tsx… | PASS |  |
| AT-962-25-4 | ResearchFlowHeader.test.tsx | PASS |  |
| AT-962-25-5 | research-nav.test.ts | PASS |  |
| AT-962-25-E-1 | - | PASS | git diff 對 app/layout.tsx、components/layout/** 零差異（本輪實跑） |
| AT-962-25-E-2 | research-workspace.test.ts | PASS |  |
| AT-962-26-1 | ResearchArchTest.java | PASS |  |
| AT-962-26-2 | test_research_delivery.py | PASS |  |
| AT-962-26-3 | test_research_delivery.py | PASS |  |
| AT-962-26-4 | ResearchArchTest.java | PASS |  |
| AT-962-26-5 | test_research_events.py | PASS |  |
| AT-962-26-E-1 | test_research_deliver_router.py | PASS |  |
| AT-962-26-E-2 | OpenApiIT.java | PASS |  |
| AT-962-27-1 | types.test.ts | PASS |  |
| AT-962-27-2 | types.test.ts,types.ts | PASS |  |
| AT-962-27-3 | types.test.ts | PASS |  |
| AT-962-27-E-1 | - | PASS | tsc --noEmit rc 0、npm run lint（含 prettier --check）通過（本輪實跑）；build 未重跑，沿主控親驗（標推論） |
| AT-962-27-E-2 | - | PASS | git log：schema.d.ts 在 P2 窗口只被 dd98bc26／65f341d4（W3）動 |
| AT-962-28-1 | test_research_int_p2.py | PASS | test_research_int_p2.py 單跑通過（Bridge 批次 541 通過 內） |
| AT-962-28-2 | test_research_int_p2.py | PASS | 同上 |
| AT-962-28-3 | test_research_int_p2.py | 載具待裁 | 本機模式載具需重建共用 backend（分類器拒絕；D-164） |
| AT-962-28-4 | research-deliver.stack.spec.ts | 載具待裁 | 同上 |
| AT-962-28-5 | - | 載具待裁 | 同上 |
| AT-962-28-6 | test_research_int_p2.py | PASS | 同上 |
| AT-962-28-7 | research-deliver.stack.spec.ts | PASS（證據檔核對） | INT 證據 §2；未重跑（會寫真棧研究專案） |
| AT-962-28-8 | research-deliver.stack.spec.ts | 裁決偏離 | 真棧回 409 非 422（D-164 D-1）；證據檔核對 |
| AT-962-28-E-1 | test_research_int_p2.py | PASS | 同上 |
| AT-962-28-E-2 | - | PASS | git worktree list 僅主樹；%TEMP% 無 r2p* 殘留；證據檔 §9 |
| AT-962-28-E-3 | test_research_delivery.py,test_research_int_p2.py | PASS | 同上 |
| AT-962-29-1 | - | PASS（含追認） | 變更檔皆在各包集合內；集合外＝orchestrator.py（D-162 追認）、docs/06_quality 證據檔（主控）；research-nav.test.ts／si.endpoints.test.ts 屬 §4 連動 |
| AT-962-29-2 | - | PASS（含註） | P2 窗口內 AutoClaude/.perf_baseline.toml＋ONBOARDING.md 差異來自主控 chore(perf) 8e437273（非 P2 包）；其餘禁區零差異 |
| AT-962-29-3 | - | PASS | TestDirEntryPrimitivesAreAccountedFor 7 個測試 OK；P2 檔無 os.replace／rename／move（grep） |
| AT-962-29-4 | - | 部分 | 僅重跑 dirent 鎖；其餘根層鎖沿主控親驗（未重跑） |
| AT-962-29-5 | - | PASS | ruff（本目錄與根視角）rc 0 |
| AT-962-29-E-1 | - | PASS | P2 四個新模組 grep 無 subprocess |
| AT-962-29-E-2 | - | PASS | fixtures/research 無 .sh |
| AT-962-29-E-3 | - | PASS | check_pytest_baseline_sites.py rc 0 |
| AT-962-30-1 | - | PASS | Architecture K.6 最後一個 sql 區塊逐字等於 V21（本輪實比）；V21_DDL.md 草案未比 |
| AT-962-30-2 | - | NOT-EVALUABLE | RELEASE_READY 勘誤批次尚未執行（流程後段） |
| AT-962-30-3 | - | NOT-EVALUABLE | RTM-P2 回填尚未執行 |
| AT-962-30-4 | - | NOT-EVALUABLE | V 系列證據以 INT 證據檔為準；尚未入 RTM |
| AT-962-30-5 | - | NOT-EVALUABLE | 出口 (a)～(i)：INT §7 顯示 (b)(c)(f) 未達（載具待裁） |
| AT-962-30-E-1 | - | NOT-EVALUABLE | RTM 尚未回填；§1.5 列數＝309 |
| AT-962-30-E-2 | - | PASS | AgentConsole/CLAUDE.md 167 行（≤200）、README.md 78 行（≤80） |

## D 突變表（副本；KILLED／SURVIVED）
**BR-P2（Bridge，24）**：B1 clip `[:limit-1]`→`[:limit]` KILLED（17_2[121]）；B2 PR 標題 60→61 KILLED（20_2[61]）；B3 unit_status 去 ESCALATED KILLED（17_3）；B4 e2e 後續 REJECTED 失效 KILLED（17_4）；**B5 `uncovered>0`→`>1` SURVIVED（F-01）**；B6 push 忽略旗標 KILLED（18_9 push-false）；B7 `push --force` KILLED；B8 detail 不遮蔽 KILLED（18_2）；**B9 `_resumable` 去 commit_sha 比對 SURVIVED（F-02）**；**B10 事件 reason[:301] SURVIVED（F-08）**；B11 遠端 sha 比對失效 KILLED（18_9 another commit）；B12 PR 內文 uncovered 改 covered KILLED（20_2）；B13 RTM `pct==100`→`>=99` KILLED（3_7）；B14 獨立性 `is not True`→`is None` KILLED（3_E_3）；B15 SCG6→SCG5 KILLED（3_5）；**B16 release_transition 去早退 SURVIVED（F-08）**；B17 PASS 不重驗 RTM KILLED（3_7）；B18 摘錄取頭 KILLED（6_4）；B19 mask 少 gitops.redact KILLED（7_2／7_1）；B20 漂移簽章去重失效 KILLED（8_3）；B21 sync 不去重 KILLED（6_2）；B22 日誌上限 +1 KILLED（6_5 釘正式值）；B23 AKIA 16→17 KILLED（7_1 AKIA）；B24 detect_spec_change 少 removeprefix SURVIVED（等價：`union_digests` 已先剝；P4 級、不列發現）。
註：首輪 Bridge 突變以 `-x -n 4` 跑，部分 KILLED 僅見 ERROR 行且 gitops 一案因副本缺 backend 原始碼而假失敗，已補齊副本並對 B5～B17、B20～B24 以第二輪重跑；上列 B5～B24 皆採第二輪結果。
**API-P2（console-api，12）**：J1 `pct!=100`→`<99` KILLED（4_3）；J2 去 scr_open 守門 KILLED（4_6）；J3 去獨立性守門 KILLED（4_4）；**J4 `push` 恆 true SURVIVED（F-03）**；J5 TAG_NAME_MAX 64→65 KILLED（19_3）；J6 fullRtm 去 pct KILLED（19_2）；J7 token 鍵改名 KILLED（20_3）；J8 去 rtm_below_100 KILLED（19_2）；J9 AKIA 16→17 KILLED（Masker 測試）；J10 reason 界 +1 KILLED（4_5）；J11 message 界 +1 KILLED（19_4）；**J12 reviewer_independent 恆 true SURVIVED（F-07）**。
**DB-P2／P2b（8）**：D1 去 SCG6 KILLED（1_E_3）；D2 V22 去 DELIVERED KILLED（1b_2）；D3 evidence_url 500→501 KILLED（1_5）；D4 https→http KILLED（1_5）；**D5 sha256 regex `{63,64}` SURVIVED（F-05）**；D6 details CHECK 弱化 KILLED（1_3）；D7 CHAR(65) KILLED（1_4）；**D8 前置守衛 `AND FALSE` SURVIVED（F-08）**。
**FE-P2A（GateRegisterDialog／HealingMonitor；F4–F8、F16–F18，8）**：F4 logLag>=0 KILLED（12_5）；F5 歸因預設字 KILLED（12_1）；**F6 effectiveResult 不強制 FAIL SURVIVED（F-04）**；**F7 reviewerIndependent 恆 true SURVIVED（F-04）**；F8 去 scrOpen 停用 KILLED（4_8）；**F16 resolved 改 some SURVIVED（F-06）**；**F17 escalatedReview 不比 taskId SURVIVED（F-06）**；F18 OPERATOR title 文案 SURVIVED（等價：測試只比「權限不足」且 READONLY_TITLE 亦含該詞；不列發現）。
**FE-P2B（10）**：F1 releaseReady 守門 KILLED（21_3）；F2 VIEWER 複製鈕 KILLED（21_6）；F3 delivered 條件 `&&`→`||` KILLED（21_E_4）；F9 tag 名界 KILLED（21_4）；F10 備註界 KILLED（21_4）；F11 PR 去 ack KILLED（21_5）；F12 uncoveredRows 判準 KILLED（17_8）；F13 PR 標題截 61 KILLED（21_5）；F14 TAG_NAME_MAX 65 KILLED（research.test D-157）；F15 GATE_REASON_MAX 501 KILLED（gateRegisterView）。
**FE-W3（5）**：W1 logLag 型別 string、W2 frTotal 可省略、W3 Kanban rtm 去 null、W4 specChange 去 null、W5 追溯 rtm 去 null：皆 KILLED，但全由 `tsc --noEmit`（rc 2）殺，`types.test.ts` rc 0（F-09）。
**合計 67：KILLED 53、SURVIVED 14（其中 2 個等價、列 P2×5／P3×3 於 B）。**
## E 跨包接縫（逐項）
| 接縫 | 判定 | 證據 |
|---|---|---|
| FE 生成型別名 vs schema.d.ts（五處手動 `\| null`、`replayed`、`logLag`、`frTotal`、追溯列 `{given,when,then}`＋`source[]`） | PASS | lib/api/types.test.ts 在 vitest 全綠（fe.xml）；`logBehind` 全 repo 零殘留；tsc rc 0；`prdSha256` 維持 narrowing 且註解引 D-152#3（任務書 §4 既定偏離） |
| console-api DTO vs Bridge 回應（`:tag` 201、`:pr` 201／200＋created、`:gates` replayed） | PASS | ResearchDeliveryApiIT／ResearchGateApiIT 全綠（backend 244 個測試／0 fail）；Bridge `status_code=201` 與 `JSONResponse(201 if created else 200)` 讀碼一致 |
| `CHECK_IDS` 七項順序＋`delivery` 鍵 | PASS | Bridge reconcile.py:54 七項；Java 測試以 BridgeSource 讀 Bridge 原始碼比對（ResearchApiIT:54）；兩者本輪皆綠 |
| `research.delivery` 固定六鍵 | PASS | delivery.py:215 六鍵；test_AT_962_18_3_4 逐鍵斷言 |
| reason 四方鎖 37＋兩份 `*_ERRATUM_PENDING` 僅 `delivery_step_failed` | PASS | ResearchReasonsTest（Java:62,64）；契約只缺 delivery_step_failed、含 tag_exists（契約:297、Architecture:1099）｜注意：research.ts:750 註解仍寫「二十二個」＝P4 過期敘述 |
| 遮蔽兩端對拍（18 筆、含 AKIA） | PASS | 夾具 JSON 18 案；HealingExcerptMaskerTest 讀同名夾具；突變 B23／J9（AKIA 位數）兩端各自被殺 |
| V21／V22 與 `LAST_VERSION=22`、游標 deliver／DELIVERED／COMPLETED、FLOW_FSM_MAPPING 新列 | PASS | V22 檔、reconcile.py:43 `deliver→{DELIVERED}`；test_AT_962_18_5 斷言游標；AT_962_1b_1～4 全綠；K.6 逐字等於 V21 |
| `GET /healing` 零 Bridge 請求＋Notifier 快取（D-149#5） | PASS | ResearchHealingApiIT 全綠（AT-9-5／8-5 含「先經 Notifier 觸發一次 sync」） |
| SCR 橫幅與漂移橫幅各單一 | PASS | BuildFrontPanel／ScrBanner／KanbanBoard 測試全綠（15-5「恰一個 scr-banner」） |
| `DELIVER_LABEL`／semver 字面單一來源（D-156／D-157） | 大致 PASS＋P4 | research.test.ts 鎖正規式；TagConfirmDialog／ReleaseActions 皆 import。殘留：PrConfirmDialog.tsx:170 送出鈕字面「建立 PR」、:149「推送到遠端」未取 `DELIVER_LABEL.createPr／pushRemote`（P4） |

## F 裁決偏離與勘誤核實
| TCS／文件位置 | TCS 字面 | 實作 | 裁決 | 仍成立？ |
|---|---|---|---|---|
| AT-962-28-8 Then | 容器模式 delivery/tag 回 422 route_unsupported_in_deployment | 真棧回 409（no_console_project／route_not_succeeded），零變化 | D-164 D-1 | 成立（INT §2 逐字） |
| AT-962-18-5、AC-962-23、IFACE §6.2／§6.6 | 游標寫入無前提 | 需 V22（LAST_VERSION≥22）；mapping 加 deliver→{DELIVERED} | D-162(a) | 成立（reconcile.py:43、V22 檔、AT_962_1b） |
| Architecture K.7／TCS AC-962-1 | 21 | 22（V22） | D-162(a) | 成立 |
| API-RP-25 totals／AT-17-x／21-5 | 無 frTotal | totals 加 frTotal | D-151 | 成立（delivery.py:141–143） |
| 契約追溯 DTO、手寫型 | gherkinSummary:string、source:string | {given,when,then}、string[] | D-158 | 成立（契約仍無追溯 DTO 條目） |
| HealingDto／IFACE | logBehind | logLag＋researchId／retryingSteps／escalatedTasks／specChange | D-161／D-163 | 成立（前端零殘留；契約未改） |
| `*_ERRATUM_PENDING` | — | 僅 delivery_step_failed | D-149#10 | 成立（契約缺列） |
| §4.1#17 `RunEventProcessor.Outcome` | — | 三參數次要建構子保留 | D-149#6 | 未逐行核（RunEventProcessor 未動突變）；測試綠 |
| AT-962-10-E-1 禁用片段 | 較寬 | `execute\|pause\|resume\|stop`＋新路徑不含 cancel\|restore\|review | D-159 | 測試綠；勘誤待批次 |
| `:tag` 續跑判準／ls-remote `^{}`／`lastRunAt` 來源／假 gh 啟動 | — | 見 D-162(b)(c)(d)(e) | D-162 | delivery.py:257–279 與測試一致 |
| `AKIA` 樣式 | 無 | 兩端加 | D-162(g) | 成立 |
| §5.7 集合外 | — | orchestrator.py +13；research-build-front.mock.spec.ts href；lib/nav／si.endpoints 測試 | D-162／D-155／§4 | 追認 |
| D-150#1 | VIEWER 複製鈕 | VIEWER 不渲染（P0 AT_960_19_6 一字未動） | D-150#1 | 成立（F2 突變殺掉） |
| AT-962-13-E-3 | LogPanel.tsx | 該檔在 execute 目錄不存在 | — | P4 規格檔名漂移 |
D-148 十四條、D-149#1/#2/#3、D-150#3/#4/#8、D-152#1/#4、D-153#1、D-157 未逐條重驗，僅由對應測試綠間接支撐（見 G）。

## G 誠實劃界
- 未重跑：Playwright docker stack spec（28-7／28-8，會寫真棧）、full `npm run build`、根層其餘鎖（僅跑 dirent 鎖、baseline 守門、ruff 兩視角）、Bridge 其餘三十餘個非 P2 測試檔。AT 判定以「測試名含 AT ID 且本輪綠」為準，個別 AT 的斷言充分性只由突變抽樣佐證。
- 副本 SDD_ROOT 指向主樹 LATEST（唯讀）；wc2 初跑時副本缺 backend 原始碼致 gitops 一案假失敗，補齊後 303 通過。Bridge 突變初輪 `-x -n 4` 的 ERROR 行不可信，以第二輪重跑為準。
- 突變執行期間並行負載使 P0 StudioPanel 三案逾時假紅（單跑 42 通過）；P4 負載敏感。
- 28-3／28-4／28-5：載具待裁，不計缺陷。30-2～30-5、30-E-1：流程後段 NOT-EVALUABLE。


## H 二審（HEAD a3e2ec5c＝57dc872a＋PKG-FIX-P2；副本 `git archive HEAD`；唯讀）
**二審判定：PASS（P1＝0、P2＝0；一審 P2×5 中 4 條由補斷言轉紅關閉、F-05 撤銷為等價突變；一審 P3／P4 順手項已核實，另有一項我方一審誤判已自我更正）。** 新發現：僅 P4×2（見 H.6）。

### H.1 十個突變於副本重做（皆應轉紅）
| 突變 | 結果 | 轉紅的測試（當回合輸出） |
|---|---|---|
| B5 `uncovered>0`→`>1`（F-01／一審 F-01） | KILLED | test_research_delivery.py::test_AT_962_18_E_2_exactly_one_uncovered_ac_still_blocks_the_tag_with_rtm_below_100 |
| B9 `_resumable` 去 commit_sha 比對（一審 F-02） | KILLED | …::test_AT_962_18_E_1_a_same_named_tag_with_a_snapshot_of_another_commit_is_409_tag_exists |
| B10 事件 reason `[:301]`（F-08） | KILLED | …::test_AT_962_18_2_the_delivery_event_reason_is_cut_at_300_characters[301] |
| B16 去 `release_transition` 早退（F-08） | KILLED（見下「更正」） | 手動套突變單跑 `-k AT_962_18_6`：`2 失敗`（新增的 …release_transition_is_a_zero_write_no_op… 與既有 …18_6_resending_after_a_full_success_writes_nothing_more）；已還原 |
| J4 `push` 恆 true（F-03） | KILLED | ResearchDeliveryApiIT > AT_962_19_1_pushOmittedOrFalseSendsPushFalseToTheBridge…（BUILD FAILED） |
| J12 `reviewer_independent` 恆 true（F-07） | KILLED | ResearchGateApiIT > AT_962_4_4_rtmVerifyForwardsReviewerIndependentFalseAndTrueIsOnlyForwarded…（BUILD FAILED） |
| F6 `effectiveResult` 不強制 FAIL（F-04） | KILLED | GateRegisterDialog.test AT_962_4_8「RELEASE_READY 送出本文一律 result:FAIL…」 |
| F7 `reviewerIndependent` 恆 true（F-04） | KILLED | AT_962_4_7「RTM_VERIFY 送出本文恰為 {gate,result:PASS,reason,reviewerIndependent:false}」 |
| F16 resolved 改 some（F-06） | KILLED | HealingMonitor.test AT_962_12_1「已修復只看該任務最後一列」 |
| F17 escalatedReview 不比 taskId（F-06） | KILLED | HealingMonitor.test AT_962_12_3「兩個任務各有一則 ESCALATED 審核…以 taskId 配對」 |
**更正（我方一審誤判）**：B16 在一審「存活」是我的 harness 把 B16 綁到 `test_research_inner_gates／deliver_router／ast_locks`，漏掉 `test_research_delivery.py`；既有 `AT_962_18_6_resending…` 本來就殺得掉它。F-08 的 B16 子項因此是**我方假發現**，非產品／測試缺陷；FIX 補的專測仍有價值（直測 `release_transition` 零寫入）。

### H.2 F-05／D5 判定：同意修復棒，D5 改列「等價突變」，F-05 撤銷
獨立驗證（本機 PG，唯讀 SELECT）：`select (repeat('a',63))::char(64) ~ '^[0-9a-f]{63,64}$', … ~ '^[0-9a-f]{64}$', (repeat('a',64))::char(64) ~ …` ⇒ `f | f | t | t`，`octet_length(63 碼 char(64))＝64`（text 轉型才是 63）。即 bpchar `~` 比對含補的空白：任何存入 CHAR(64) 的值恆為 64 字元，`{63,64}` 要通過就必須整串 64 碼皆 hex，與 `{64}` 無輸入可區分。一審對 `{63,64}` 跑 ResearchSchemaMigrationIT 的存活結果與此相符，且 `AT_962_1_4` 負控本就含 `"a".repeat(63)`（我一審誤稱「缺 63 碼負控」，更正）。FIX 在測試加註解說明等價；ResearchSchemaMigrationIT 本輪 102 個測試（含另三類別）全綠。

### H.3 順手項核實
| 項 | 結果 |
|---|---|
| F-09 types.test.ts | 檔頭註解說明型別鎖由 tsc 承擔、vitest 僅鎖鍵集合（只改註解；與一審建議之一相符）✓ |
| F-10 AT 命名 | 5-6：test_sdd_cli.py 新案 `test_AT_962_5_6_…`；18-4／18-E-4：test_research_delivery.py 以註解＋參數 ids（`AT_962_18_E_4-*`）補 ID；13-E-3：TerminalPane.test 新案（LiveLogCard／useRunStream／LogPanel 存在且不含研究面字樣；LogPanel 實際在 components/domain，與我一審所稱「execute 目錄」不同路徑，已吸收）✓；24-E-3 另見 AT_961_15_4（未改）可接受 |
| F-11 research.ts 註解 | 改「三十七個＝P0 二十二＋P1 十三＋P2 二」✓ |
| F-12 PrConfirmDialog | 送出鈕與失敗步驟字面改取 `DELIVER_LABEL.createPr／pushRemote`（diff 4 行）✓；vitest PrConfirmDialog 綠 |
| F-13 push 驗證 | `isinstance(body.get("push", False), bool)`；新參數化測試 push∈{1,0,"true","false",None,[],{}} 皆 422 `invalid_request`、rule=`invalid_boolean`、零 git 呼叫零列 ✓ |
| F-17 D-3 | 兩子 router 檔尾 `_parent_router.include_router(router)`；`research.py` 檔尾只 import 不取 `.router`；新測試於**乾淨子行程**分別先匯入 `research_deliver`／`research_scr` 與經父模組，比較 OpenAPI `METHOD path` 清單相等且含 `:tag`、`:scr` ✓；AST 鎖與能力登記（test_research_ast_locks／test_research_capability）本輪綠 ✓（讀碼：父檔尾 import 時 `router` 已定義、子模組半初始化不被存取，兩入口序皆成立） |
| F-17 D-4 | `gherkin_summary` 先剔除 `lstrip().startswith("```")` 的行；新測試圍欄與縮排圍欄皆不入摘要、圍欄內文字保留 ✓。限制（推論，P4）：只剔「以圍欄起頭的行」，行內中段出現 ``` 不處理 |

### H.4 全面回歸（副本 a3e2ec5c，當回合）
- Bridge：14 個檔（含 ast_locks、capability、deliver_router、delivery、gitops、healing、inner_gates、reconcile、scr、sdd_cli、adopt、fsm_ops…）`928 通過`、ruff rc 0（SDD_ROOT 指向主樹 v0.30）。
- backend：ResearchDeliveryApiIT／ResearchGateApiIT／ResearchReasonsTest／ResearchSchemaMigrationIT `102 個測試, 102 成功, 0 failures, 0 略過`，BUILD SUCCESSFUL（rc 0）。
- frontend：GateRegisterDialog／HealingMonitor／TerminalPane／PrConfirmDialog／types／research 六檔 `153 通過`。

### H.5 抽讀（一審批次跑過但未逐條讀斷言的 AT；本輪讀測試本體）
| AT | 讀後判斷 |
|---|---|
| 18-7 | 壞 origin 先 502 push 失敗、本地 tag 保留、列 0、FSM 仍 RELEASE_READY；改好 origin 重送 201、無 `--force`／`-f`、列恰一、FSM RELEASE ✓ 斷言充分 |
| 20-6 | gh 洩漏模式下 token 不在回應、argv、DB 全文字欄、caplog、gh 呼叫 argv ✓ |
| 17-E-4 | 偽造 rows／totals 被忽略，仍 409 rtm_below_100 且零 git 呼叫 ✓ |
| 18-E-5 | 漂移先於狀態檢查與 git；422 digest_mismatch、drift 三鍵、快照未生、檔不被還原 ✓ |
| 26-3 | DB 阻塞時 outbox 暫存、replay 寫一次、重放不重複 ✓ |
| 9-5（Java） | 先無快取＝null／0；經 Notifier 觸發一次 sync 後 logLag＝view_rows−log_lines＝2、logSyncedThrough 取視圖列序 ✓（注意：以 `Thread.onSpinWait()` 忙等至多 5 秒，CPU 浪費但不影響判準；P4） |
| 22-E-1 | 失敗 tag：502、交付列 0、audit 恰 +1 ✓ |
| 16-2（FE） | 合法 researchId 有回連、href、位於「返回專案」之後；非 UUID 不顯示 ✓ |
| 25-3（FE） | 工作區單一 drift-banner、`build-drift-banner` 不存在、原始碼掃描 ✓ |
| 21-E-4（FE） | RELEASE＋Tag 列＝已建立停用；Tag 列在但 FSM 仍 RELEASE_READY＝續跑可重送；FAILED 列不算 ✓ |
| 15-5（FE ScrBanner） | scrOpen 橫幅文案、啟動類動作停用同一句登記文案；false 不渲染 ✓ |
共 11 條，斷言皆有鑑別力，未發現新缺口。

### H.6 新發現（僅 P4）
- N-1（P4）：ResearchHealingApiIT AT-9-5 以忙等（`Thread.onSpinWait`）等快取，高負載下仍有 5 秒上界逾時風險，宜改 `Awaitility`／有界 sleep。
- N-2（P4，推論）：D-4 圍欄剔除只認「行首圍欄行」，行內 ``` 不處理；現行 AC 夾具型態不觸發。
未重審：F-14／F-15／F-18 維持勘誤、F-16 沿既有名單（依指示）。工作樹上 INT 續棒未 commit 的兩檔未讀（一律讀 archive 副本）。
