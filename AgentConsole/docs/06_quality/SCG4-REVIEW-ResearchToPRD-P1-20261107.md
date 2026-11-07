# SCG4-REVIEW-ResearchToPRD-P1（2026-11-07；鍵 `agentconsole-research-to-prd-p1`）

> 主控落檔說明：本檔由獨立 QA 鏡（Sonnet）在 scratchpad 寫成，一審（HEAD `8380142a`，判 FAIL：P1 0／P2 3）
> 與二審（HEAD `92d50ccd`，判 **PASS**：P1 0／P2 0／P3 4／P4 2）兩段並存，**最終判定以文末〈二審 A〉為準**。
> 一審三條 P2（F-01 前端 `failure_step` 真實形態、F-02 D-143(3) `imported_tasks_count`、F-10 `gitops.redact`
> 對 `%5F` 編碼形態**真外洩**）由修復棒於 `92d50ccd` 修畢並經二審副本突變確認；一審 P3 的 F-11／F-12 由 FIX2
> 補測試（見 `git log` 的 PKG-FIX2-P1 commit）；仍開的 P3＝F-05（根層名冊勘誤）、F-06（RTM 回填指向實際測試名）、
> F-13（`%XX` 小寫與空白切開兩子特性無測試）、F-14（AT-961-10-6 相等斷言自證式）。英文計數字樣（passed／skipped／
> tests）在本檔一律改為中文，以符合基線數字守門；數字本身未改。

# SCG-4 一審報告：ResearchToPRD P1（二審補完版；審查 HEAD 8380142a，程式與 cef5bcd7 零差異）

## A 摘要與判定
- 判定：**FAIL**（P2 三條：F-01、F-02、F-10；P1 0）。規則：P1 0 且 P2 0 才 PASS。
- 計數：P1 0／P2 3／P3 7（F-03、04、05、06、09、11、12）／P4 2（F-07、等價雙重防護）。
- 實跑（皆在 HEAD 的唯讀指令或 `git archive` 副本；主工作樹未動）：
  - Bridge 研究子集 `pytest tests -k "research and not int_p1" -n 6`（`BRIDGE_TEST_DSN` 指本機拋棄式庫）：**1271 通過, 1 略過（655 s），rc=0**。
  - backend 13 個研究相關類別（ResearchFlowPolicyTest、ResearchReasonsTest、ResearchBridgeShapeTest、ResearchArchTest、BridgeHttpAdapterResearchTest、ResearchRouteApiIT、ResearchScrApiIT、ResearchDecompositionApiIT、ResearchSchemaMigrationIT、ResearchApiIT、OpenApiIT、RbacIT、BackupJobMigrationIT；副本 `gradlew cleanTest test --tests …`）：`Test result: SUCCESS (172 個測試, 172 成功, 0 failures, 0 略過)`，BUILD SUCCESSFUL，rc=0。
  - 前端全套（副本）：2345 通過，128／129 檔過；唯一失敗檔 `backup-docs.test.ts` 因副本缺 `AgentConsole/docker/README.md`（ENOENT），與 P1 無關（推論：真樹會過）。
  - ruff 兩視角（`ruff check .` 於 engine-bridge、`ruff check AgentConsole/engine-bridge` 於根）皆 rc=0。
- 突變合計 52（有效、去重）：KILLED 41／SURVIVED 11（4 個等價；7 個非等價＝F-01、F-03、F-04、F-09、F-10、F-11、F-12）。
- 未做／未評估：見 §C.2、§G。

## B 發現表
| 編號 | 級 | 座標 | 問題 | 修法／歸屬 |
|---|---|---|---|---|
| F-01 | **P2** | `AgentConsole/frontend/lib/domain/research.ts` `researchErrorText`（`error.details?.failureStep ?? error.details?.failure_step`）；測試 `lib/domain/research.test.ts:1226-1230`、`components/domain/research/RoutePanel.test.tsx:101` | 真實 502 `route_step_failed` 的 `details` 由契約透傳 snake_case `failure_step`（`ResearchErrorDocs.java:99`、`schema.d.ts:8779`），只有 snake_case 分支承擔真實流量；前端測試只餵 camelCase。突變「刪掉 `?? failure_step`」→ vitest 87 通過＝SURVIVED。 | FE 修復棒：兩處各補一案 `details:{failure_step:"GIT_SWITCH"}`，斷言文案含「建立分支與工作樹」。 |
| F-02 | **P2** | `ResearchDecompositionService.java` 簽核本文；`engine-bridge/tests/test_research_decompose.py:377-405`（AT-961-10-6） | D-143(3) 仍未做：`git grep imported_tasks_count -- AgentConsole` 零命中；10-6 後半「tasks_count 等於已簽核版本落成的正式 tasks 數」無斷言（測試 docstring 自承）。 | 依 D-143(3)：簽核本文加 `imported_tasks_count`、Bridge 記進簽核版 artifact、10-6 斷言相等（backend＋Bridge）。 |
| F-10 | **P2** | `tests/test_research_route_b.py:275-295`（AT-961-6-E-2）；產品碼 `gitops.py:99` | 斷言只判 `secret not in out and secret[:8] not in out`；百分號編碼形態即使完全未被去敏，輸出也不含明文 ⇒ 斷言恆真。突變「`forms = {secret}`」在 gitops＋route_a／b／exec 四檔（96 通過）SURVIVED。token 零外洩屬安全條款。 | Bridge 測試修復棒：編碼案加 `assert TOKEN.replace('_','%5F') not in out`。產品碼現況看起來正確。 |
| F-03 | P3 | `PublicRepoConfirm.tsx:35`；`PublicRepoConfirm.test.tsx` | 突變「`value !== "" &&` 拿掉」SURVIVED：空輸入不顯示錯誤無斷言。 | 補斷言。 |
| F-04 | P3 | `lib/domain/research.ts` `routeIsActive` | 突變「PENDING 不算進行中」SURVIVED。 | 補 `routeIsActive("PENDING")===true` 斷言。 |
| F-05 | P3 | `tools/tests/test_windowsapps_guard_bash_parity.py`（commit `fee50a4a`、`0af3a6bc`） | 根層 `tools/` 被動：假 gh POSIX 夾具目錄須補列名冊；AT-961-23-1「禁區零差異」與 TCS §5.7／§4 均未預告。pre-push 閘逼出的主控修補。 | RELEASE_READY 勘誤補列（裁決偏離，非缺陷）。 |
| F-06 | P3 | AT-961-9-E-1／9-E-2、13-9、19-3、19-6、20-E-1、22-8、23-x、24-1 | 14 個 AT 在 repo 無 `AT_961_` 命名測試。行為多由他案覆蓋：9-E-1←`test_AT_961_9_4_…`（`test_research_tcs_draft.py:202-242`）；9-E-2 承接半←`test_AT_961_10_7_…`，「失敗後再啟動走完成功路徑」由 9-3＋9-4 合起來覆蓋、無單一案；19-3／19-6←`stateKeys.test.ts`／`design-rules.test.ts` 全域掃描；13-9←`test_research_scr_fsm.py:130`；20-E-1←`test_research_reconcile.py:505`；23-x、24-1 為 Gate 指令。 | RTM 回填時把 AT 編號指向實際測試名。 |
| F-09 | P3 | `scr.py:254-262` `open_minor` 補償（轉態失敗⇒SCR 標 REJECTED） | 突變「REJECTED→OPEN」SURVIVED；TCS 無此行為的 AT。 | 補一案。 |
| F-11 | P3 | `outbox.py:305-312` `bind_fsm_reader` 補校正 `_unsettled`；`orchestrator.py:258` | 晚綁定分支零測試引用（`git grep` 零命中）；突變「`if ids and not pending`→`if False`」在 route_exec 25 通過＝SURVIVED。TCS AT-961-4-E-1 未要求此分支（D-128 延伸）。 | 補一案：先重放後綁讀取器，斷言游標被校正。 |
| F-12 | P3 | `ResearchExecutionGuard.java` `STALE_STATUSES = Set.of("STALE","REJECTED")` | 去掉 `"STALE"`：IT 33 個測試 全過＝SURVIVED。推論：有效拆解查詢只回已簽核版，該字面不可達或缺 AT。 | 補 AT 或刪字面並寫理由。 |
| F-07 | P4 | `scaffold.py:177-186` `workspace_files` | 推論：`rglob` 可能穿越符號連結目錄；`is_file()`／`is_symlink()` 只擋檔層級連結。工作區由 Bridge 自建，暴露低。 | 記錄。 |
| — | P4 | `gitops.check_path` 拒 `-` 起頭與 `_parse_add` 同款檢查 | 重複防護，拿掉一處無行為差異（等價突變）。 | 無。 |
| F-08 | 撤回 | `outbox._settle_cursors` 說明字 | 已讀 `db.py:467-471`：「與現值相同＝跳過」成立。 | 無 |


## C AT 逐條表（209 個 AT）
方法說明：TCS 的 AT 以測試名／檔內字樣對映（work\at_map.json）。**逐條單跑未做**——改為整批聚合實跑，聚合結果見 §A；個別 AT 的「判定」欄寫該 AT 所屬套件的聚合結果，這不等於逐條單跑 rc。分類統計：backend 49、Bridge 109、前端 18、E2E／前端 10、E2E／INT 2、INT 4、純 E2E 3、Gate 6、無命名測試 8。

### C.1 表
| AT | 測試檔（短名） | 判定 |
|---|---|---|
| AT-961-1-1 |  | backend 172/0 fail rc0 |
| AT-961-1-2 |  | backend 172/0 fail rc0 |
| AT-961-1-3 |  | backend 172/0 fail rc0 |
| AT-961-1-4 |  | backend 172/0 fail rc0 |
| AT-961-1-5 |  | backend 172/0 fail rc0 |
| AT-961-1-6 |  | backend 172/0 fail rc0 |
| AT-961-1-7 |  | backend 172/0 fail rc0 |
| AT-961-1-8 |  | backend 172/0 fail rc0 |
| AT-961-1-9 |  | backend 172/0 fail rc0 |
| AT-961-1-E-1 |  | backend 172/0 fail rc0 |
| AT-961-1-E-2 |  | backend 172/0 fail rc0 |
| AT-961-1-E-3 |  | backend 172/0 fail rc0 |
| AT-961-2-1 | test_research_route_gate.py | Bridge 1271 通過 rc0 |
| AT-961-2-2 | test_research_route_gate.py | Bridge 1271 通過 rc0 |
| AT-961-2-3 | test_research_route_gate.py | Bridge 1271 通過 rc0 |
| AT-961-2-4 | test_research_route_gate.py | Bridge 1271 通過 rc0 |
| AT-961-2-5 | test_research_route_gate.py | Bridge 1271 通過 rc0 |
| AT-961-2-6 | test_research_route_gate.py | Bridge 1271 通過 rc0 |
| AT-961-2-7 | test_research_route_gate.py | Bridge 1271 通過 rc0 |
| AT-961-2-E-1 | test_research_route_gate.py | Bridge 1271 通過 rc0 |
| AT-961-3-1 | test_research_route_gate.py | Bridge 1271 通過 rc0 |
| AT-961-3-2 | test_research_route_gate.py | Bridge 1271 通過 rc0 |
| AT-961-3-3 | test_research_route_gate.py | Bridge 1271 通過 rc0 |
| AT-961-3-4 | test_research_route_gate.py | Bridge 1271 通過 rc0 |
| AT-961-3-5 | test_research_route_gate.py | Bridge 1271 通過 rc0 |
| AT-961-3-6 | test_research_route_gate.py | Bridge 1271 通過 rc0 |
| AT-961-3-7 | test_research_route_gate.py | Bridge 1271 通過 rc0 |
| AT-961-3-E-1 | test_research_route_gate.py | Bridge 1271 通過 rc0 |
| AT-961-4-1 | test_research_route_exec.py | Bridge 1271 通過 rc0 |
| AT-961-4-2 | test_research_route_exec.py | Bridge 1271 通過 rc0 |
| AT-961-4-3 | test_research_route_exec.py | Bridge 1271 通過 rc0 |
| AT-961-4-4 | test_research_route_exec.py | Bridge 1271 通過 rc0 |
| AT-961-4-5 | test_research_route_exec.py | Bridge 1271 通過 rc0 |
| AT-961-4-6 | test_research_route_exec.py | Bridge 1271 通過 rc0 |
| AT-961-4-7 | test_research_route_exec.py | Bridge 1271 通過 rc0 |
| AT-961-4-8 | test_research_route_exec.py | Bridge 1271 通過 rc0 |
| AT-961-4-9 | test_research_route_exec.py | Bridge 1271 通過 rc0 |
| AT-961-4-E-1 | test_research_route_exec.py | Bridge 1271 通過 rc0 |
| AT-961-4-E-2 | test_research_route_exec.py | Bridge 1271 通過 rc0 |
| AT-961-4-E-3 | test_research_route_exec.py | Bridge 1271 通過 rc0 |
| AT-961-5-1 | test_research_route_a.py | Bridge 1271 通過 rc0 |
| AT-961-5-2 | test_research_route_a.py | Bridge 1271 通過 rc0 |
| AT-961-5-3 | test_research_route_a.py | Bridge 1271 通過 rc0 |
| AT-961-5-4 | test_research_route_a.py | Bridge 1271 通過 rc0 |
| AT-961-5-5 | test_research_route_a.py | Bridge 1271 通過 rc0 |
| AT-961-5-6 | test_research_route_a.py | Bridge 1271 通過 rc0 |
| AT-961-5-E-1 | test_research_route_a.py | Bridge 1271 通過 rc0 |
| AT-961-6-1 | test_research_scaffold.py | Bridge 1271 通過 rc0 |
| AT-961-6-2 | test_research_scaffold.py | Bridge 1271 通過 rc0 |
| AT-961-6-3 | test_research_scaffold.py | Bridge 1271 通過 rc0 |
| AT-961-6-4 | test_research_route_b.py, test_research_scaffold.py | Bridge 1271 通過 rc0 |
| AT-961-6-5 | test_research_route_b.py | Bridge 1271 通過 rc0 |
| AT-961-6-6 | test_research_route_b.py | Bridge 1271 通過 rc0 |
| AT-961-6-7 | test_research_route_b.py | Bridge 1271 通過 rc0 |
| AT-961-6-8 | test_research_route_b.py | Bridge 1271 通過 rc0 |
| AT-961-6-9 | test_research_scaffold.py | Bridge 1271 通過 rc0 |
| AT-961-6-E-1 | test_research_route_b.py | Bridge 1271 通過 rc0 |
| AT-961-6-E-2 | test_research_route_b.py | Bridge 1271 通過 rc0 |
| AT-961-7-1 | test_research_adopt.py | Bridge 1271 通過 rc0 |
| AT-961-7-2 | test_research_adopt.py | Bridge 1271 通過 rc0 |
| AT-961-7-3 | test_research_adopt.py | Bridge 1271 通過 rc0 |
| AT-961-7-4 | test_research_adopt.py | Bridge 1271 通過 rc0 |
| AT-961-7-5 | test_research_adopt.py | Bridge 1271 通過 rc0 |
| AT-961-7-6 | test_research_adopt.py, test_research_fsm_ops.py | Bridge 1271 通過 rc0 |
| AT-961-7-7 | test_research_fsm_ops.py | Bridge 1271 通過 rc0 |
| AT-961-7-E-1 | test_research_adopt.py | Bridge 1271 通過 rc0 |
| AT-961-7-E-2 | test_research_adopt.py | Bridge 1271 通過 rc0 |
| AT-961-8-1 | test_research_gitops.py | Bridge 1271 通過 rc0 |
| AT-961-8-2 | test_research_gitops.py | Bridge 1271 通過 rc0 |
| AT-961-8-3 | test_research_gitops.py | Bridge 1271 通過 rc0 |
| AT-961-8-4 | test_research_gitops.py | Bridge 1271 通過 rc0 |
| AT-961-8-5 | test_research_ast_locks.py, test_research_capability.py | Bridge 1271 通過 rc0 |
| AT-961-8-6 | test_research_ast_locks.py | Bridge 1271 通過 rc0 |
| AT-961-8-7 | test_research_gitops.py | Bridge 1271 通過 rc0 |
| AT-961-8-E-1 | test_research_gitops.py | Bridge 1271 通過 rc0 |
| AT-961-8-E-2 | test_research_gitops.py | Bridge 1271 通過 rc0 |
| AT-961-9-1 | test_research_tcs_draft.py | Bridge 1271 通過 rc0 |
| AT-961-9-2 | test_research_tcs_draft.py | Bridge 1271 通過 rc0 |
| AT-961-9-3 | test_research_tcs_draft.py | Bridge 1271 通過 rc0 |
| AT-961-9-4 | test_research_tcs_draft.py | Bridge 1271 通過 rc0 |
| AT-961-9-5 | test_research_tcs_draft.py | Bridge 1271 通過 rc0 |
| AT-961-9-6 | test_research_tcs_draft.py | Bridge 1271 通過 rc0 |
| AT-961-9-7 | test_research_tcs_draft.py | Bridge 1271 通過 rc0 |
| AT-961-9-E-1 |  | F-06（行為由他案覆蓋，見 B 表） |
| AT-961-9-E-2 |  | F-06（行為由他案覆蓋，見 B 表） |
| AT-961-10-1 | test_research_decompose.py | Bridge 1271 通過 rc0 |
| AT-961-10-2 | test_research_decompose.py | Bridge 1271 通過 rc0 |
| AT-961-10-3 | test_research_decompose.py | Bridge 1271 通過 rc0 |
| AT-961-10-4 | test_research_decompose.py | Bridge 1271 通過 rc0 |
| AT-961-10-5 | test_research_decompose.py | Bridge 1271 通過 rc0 |
| AT-961-10-6 | test_research_decompose.py | Bridge 1271 通過 rc0 |
| AT-961-10-7 | test_research_decompose.py | Bridge 1271 通過 rc0 |
| AT-961-10-8 | test_research_decompose.py | Bridge 1271 通過 rc0 |
| AT-961-10-E-1 | test_research_decompose.py | Bridge 1271 通過 rc0 |
| AT-961-11-1 |  | backend 172/0 fail rc0 |
| AT-961-11-2 |  | backend 172/0 fail rc0 |
| AT-961-11-3 |  | backend 172/0 fail rc0 |
| AT-961-11-4 |  | backend 172/0 fail rc0 |
| AT-961-11-5 |  | backend 172/0 fail rc0 |
| AT-961-11-6 |  | backend 172/0 fail rc0 |
| AT-961-11-7 | BridgeHttpAdapterResearchTest.java | backend 172/0 fail rc0 |
| AT-961-11-E-1 |  | backend 172/0 fail rc0 |
| AT-961-11-E-2 |  | backend 172/0 fail rc0 |
| AT-961-12-1 | test_research_scr.py | Bridge 1271 通過 rc0 |
| AT-961-12-2 | test_research_scr.py | Bridge 1271 通過 rc0 |
| AT-961-12-3 | test_research_scr.py | Bridge 1271 通過 rc0 |
| AT-961-12-4 | test_research_scr.py | Bridge 1271 通過 rc0 |
| AT-961-12-5 | test_research_scr.py | Bridge 1271 通過 rc0 |
| AT-961-12-6 | test_research_scr.py | Bridge 1271 通過 rc0 |
| AT-961-12-7 | test_research_scr.py | Bridge 1271 通過 rc0 |
| AT-961-12-E-1 | test_research_scr.py | Bridge 1271 通過 rc0 |
| AT-961-13-1 | test_research_scr_fsm.py | Bridge 1271 通過 rc0 |
| AT-961-13-2 | test_research_scr_fsm.py | Bridge 1271 通過 rc0 |
| AT-961-13-3 | test_research_scr_fsm.py | Bridge 1271 通過 rc0 |
| AT-961-13-4 | test_research_scr_fsm.py | Bridge 1271 通過 rc0 |
| AT-961-13-5 | test_research_scr_fsm.py | Bridge 1271 通過 rc0 |
| AT-961-13-6 | test_research_scr_fsm.py | Bridge 1271 通過 rc0 |
| AT-961-13-7 | test_research_scr_fsm.py | Bridge 1271 通過 rc0 |
| AT-961-13-8 | test_research_scr_fsm.py | Bridge 1271 通過 rc0 |
| AT-961-13-9 |  | F-06（行為由他案覆蓋，見 B 表） |
| AT-961-13-E-1 | test_research_scr_fsm.py | Bridge 1271 通過 rc0 |
| AT-961-13-E-2 | test_research_scr_fsm.py | Bridge 1271 通過 rc0 |
| AT-961-13-E-3 | test_research_scr_fsm.py | Bridge 1271 通過 rc0 |
| AT-961-14-1 |  | backend 172/0 fail rc0 |
| AT-961-14-2 |  | backend 172/0 fail rc0 |
| AT-961-14-3 |  | backend 172/0 fail rc0 |
| AT-961-14-4 |  | backend 172/0 fail rc0 |
| AT-961-14-5 |  | backend 172/0 fail rc0 |
| AT-961-14-6 |  | backend 172/0 fail rc0 |
| AT-961-14-7 |  | backend 172/0 fail rc0 |
| AT-961-14-8 | BridgeHttpAdapterResearchTest.java | backend 172/0 fail rc0 |
| AT-961-14-E-1 |  | backend 172/0 fail rc0 |
| AT-961-14-E-2 |  | backend 172/0 fail rc0 |
| AT-961-15-1 |  | backend 172/0 fail rc0 |
| AT-961-15-2 |  | backend 172/0 fail rc0 |
| AT-961-15-3 |  | backend 172/0 fail rc0 |
| AT-961-15-4 | ResearchReasonsTest.java | backend 172/0 fail rc0 |
| AT-961-15-5 | ResearchArchTest.java | backend 172/0 fail rc0 |
| AT-961-15-6 |  | backend 172/0 fail rc0 |
| AT-961-15-7 | ResearchFlowPolicyTest.java | backend 172/0 fail rc0 |
| AT-961-15-8 | ResearchBridgeShapeTest.java | backend 172/0 fail rc0 |
| AT-961-15-9 |  | backend 172/0 fail rc0 |
| AT-961-15-E-1 |  | backend 172/0 fail rc0 |
| AT-961-15-E-2 |  | backend 172/0 fail rc0 |
| AT-961-16-1 | test_research_capabilities_p1.py | Bridge 1271 通過 rc0 |
| AT-961-16-2 | test_research_capabilities_p1.py | Bridge 1271 通過 rc0 |
| AT-961-16-3 | test_research_capabilities_p1.py | Bridge 1271 通過 rc0 |
| AT-961-16-4 |  | backend 172/0 fail rc0 |
| AT-961-16-5 | RouteDrawer.test.tsx, research-route.mock.spec.ts, research-workspace.test.ts, route.ts | 前端 128/129 檔過（唯一失敗檔＝副本缺 docker/README.md，非 P1）；＋Playwright 未重跑 |
| AT-961-16-E-1 | test_research_capabilities_p1.py | Bridge 1271 通過 rc0 |
| AT-961-16-E-2 | RouteDrawer.test.tsx | 前端 128/129 檔過（唯一失敗檔＝副本缺 docker/README.md，非 P1） |
| AT-961-17-1 | RouteDrawer.test.tsx, research-route.mock.spec.ts | 前端 128/129 檔過（唯一失敗檔＝副本缺 docker/README.md，非 P1）；＋Playwright 未重跑 |
| AT-961-17-2 | RoutePanel.test.tsx | 前端 128/129 檔過（唯一失敗檔＝副本缺 docker/README.md，非 P1） |
| AT-961-17-3 | RouteCardA.test.tsx, RouteDrawer.test.tsx | 前端 128/129 檔過（唯一失敗檔＝副本缺 docker/README.md，非 P1） |
| AT-961-17-4 | PublicRepoConfirm.test.tsx, RouteCardB.test.tsx, RouteDrawer.test.tsx, research-route.mock.spec.ts | 前端 128/129 檔過（唯一失敗檔＝副本缺 docker/README.md，非 P1）；＋Playwright 未重跑 |
| AT-961-17-5 | RouteActionList.test.tsx, RouteDrawer.test.tsx, research-route.mock.spec.ts | 前端 128/129 檔過（唯一失敗檔＝副本缺 docker/README.md，非 P1）；＋Playwright 未重跑 |
| AT-961-17-6 | RouteDrawer.test.tsx, research-route.mock.spec.ts | 前端 128/129 檔過（唯一失敗檔＝副本缺 docker/README.md，非 P1）；＋Playwright 未重跑 |
| AT-961-17-7 | RoutePanel.test.tsx, RouteStepsTimeline.test.tsx | 前端 128/129 檔過（唯一失敗檔＝副本缺 docker/README.md，非 P1） |
| AT-961-17-8 | RoutePanel.test.tsx, research-route.mock.spec.ts | 前端 128/129 檔過（唯一失敗檔＝副本缺 docker/README.md，非 P1）；＋Playwright 未重跑 |
| AT-961-17-E-1 | RouteDrawer.test.tsx | 前端 128/129 檔過（唯一失敗檔＝副本缺 docker/README.md，非 P1） |
| AT-961-17-E-2 | research.test.ts | 前端 128/129 檔過（唯一失敗檔＝副本缺 docker/README.md，非 P1） |
| AT-961-18-1 | BuildFrontPanel.test.tsx, a11y.mock.spec.ts, research-build-front.mock.spec.ts | 前端 128/129 檔過（唯一失敗檔＝副本缺 docker/README.md，非 P1）；＋Playwright 未重跑 |
| AT-961-18-2 | BuildFrontPanel.test.tsx | 前端 128/129 檔過（唯一失敗檔＝副本缺 docker/README.md，非 P1） |
| AT-961-18-3 | BuildFrontPanel.test.tsx | 前端 128/129 檔過（唯一失敗檔＝副本缺 docker/README.md，非 P1） |
| AT-961-18-4 | BuildFrontPanel.test.tsx, research-build-front.mock.spec.ts | 前端 128/129 檔過（唯一失敗檔＝副本缺 docker/README.md，非 P1）；＋Playwright 未重跑 |
| AT-961-18-5 | BuildFrontPanel.test.tsx | 前端 128/129 檔過（唯一失敗檔＝副本缺 docker/README.md，非 P1） |
| AT-961-18-6 | BuildFrontPanel.test.tsx, research-build-front.mock.spec.ts | 前端 128/129 檔過（唯一失敗檔＝副本缺 docker/README.md，非 P1）；＋Playwright 未重跑 |
| AT-961-18-7 | BuildFrontPanel.test.tsx | 前端 128/129 檔過（唯一失敗檔＝副本缺 docker/README.md，非 P1） |
| AT-961-18-E-1 | BuildFrontPanel.test.tsx, research-build-front.mock.spec.ts | 前端 128/129 檔過（唯一失敗檔＝副本缺 docker/README.md，非 P1）；＋Playwright 未重跑 |
| AT-961-19-1 | ResearchWorkspaceView.test.tsx | 前端 128/129 檔過（唯一失敗檔＝副本缺 docker/README.md，非 P1） |
| AT-961-19-2 | research-workspace.test.ts | 前端 128/129 檔過（唯一失敗檔＝副本缺 docker/README.md，非 P1） |
| AT-961-19-3 |  | F-06（行為由他案覆蓋，見 B 表） |
| AT-961-19-4 | FlowStepper.test.tsx | 前端 128/129 檔過（唯一失敗檔＝副本缺 docker/README.md，非 P1） |
| AT-961-19-5 | endpoints.test.ts | 前端 128/129 檔過（唯一失敗檔＝副本缺 docker/README.md，非 P1） |
| AT-961-19-6 |  | F-06（行為由他案覆蓋，見 B 表） |
| AT-961-19-E-1 | research.test.ts | 前端 128/129 檔過（唯一失敗檔＝副本缺 docker/README.md，非 P1） |
| AT-961-20-1 | test_research_reconcile.py | Bridge 1271 通過 rc0 |
| AT-961-20-2 | test_research_reconcile.py | Bridge 1271 通過 rc0 |
| AT-961-20-3 | test_research_reconcile.py | Bridge 1271 通過 rc0 |
| AT-961-20-4 | test_research_reconcile.py | Bridge 1271 通過 rc0 |
| AT-961-20-E-1 |  | F-06（行為由他案覆蓋，見 B 表） |
| AT-961-20-E-2 | research.test.ts | 前端 128/129 檔過（唯一失敗檔＝副本缺 docker/README.md，非 P1） |
| AT-961-20-E-3 |  | backend 172/0 fail rc0 |
| AT-961-20-E-4 | BuildFrontPanel.test.tsx | 前端 128/129 檔過（唯一失敗檔＝副本缺 docker/README.md，非 P1） |
| AT-961-21-1 |  | backend 172/0 fail rc0 |
| AT-961-21-2 |  | backend 172/0 fail rc0 |
| AT-961-21-E-1 |  | backend 172/0 fail rc0 |
| AT-961-22-1 | research-route-local.stack.spec.ts, test_research_int_p1.py | INT 檔本鏡未重跑；＋Playwright 未重跑 |
| AT-961-22-2 | research-route-local.stack.spec.ts, test_research_int_p1.py | INT 檔本鏡未重跑；＋Playwright 未重跑 |
| AT-961-22-3 | test_research_int_p1.py | INT 檔本鏡未重跑 |
| AT-961-22-4 | test_research_int_p1.py | INT 檔本鏡未重跑 |
| AT-961-22-5 | research-p1-docker.stack.spec.ts | NOT-EVALUABLE（本鏡未重跑 Playwright；INT 證據檔自報全過） |
| AT-961-22-6 | research-p1-docker.stack.spec.ts | NOT-EVALUABLE（本鏡未重跑 Playwright；INT 證據檔自報全過） |
| AT-961-22-7 | a11y.mock.spec.ts, research-route.mock.spec.ts | NOT-EVALUABLE（本鏡未重跑 Playwright；INT 證據檔自報全過） |
| AT-961-22-8 |  | F-06（行為由他案覆蓋，見 B 表） |
| AT-961-22-E-1 | test_research_int_p1.py | INT 檔本鏡未重跑 |
| AT-961-22-E-2 | test_research_int_p1.py | INT 檔本鏡未重跑 |
| AT-961-23-1 |  | 見 §C.2 |
| AT-961-23-2 |  | 見 §C.2 |
| AT-961-23-3 |  | 見 §C.2 |
| AT-961-23-4 |  | 見 §C.2 |
| AT-961-23-5 |  | 見 §C.2 |
| AT-961-23-E-1 |  | F-06（行為由他案覆蓋，見 B 表） |
| AT-961-24-1 |  | 見 §C.2 |
| AT-961-25-1 | ResearchFlowPolicyTest.java | backend 172/0 fail rc0 |
| AT-961-25-2 | test_research_reconcile.py | Bridge 1271 通過 rc0 |
| AT-961-25-3 |  | backend 172/0 fail rc0 |
| AT-961-25-4 | BuildFrontPanel.test.tsx | 前端 128/129 檔過（唯一失敗檔＝副本缺 docker/README.md，非 P1） |
| AT-961-25-E-1 | test_research_reconcile.py | Bridge 1271 通過 rc0 |

### C.2 未通過／未評估者清單
- 無任何已跑 AT 失敗（聚合全綠）；問題來自**鑑別力**（B 表 F-01、F-02、F-10）：對應 AT-961-17-7／19-E-1（F-01）、AT-961-10-6（F-02）、AT-961-6-E-2（F-10）判為「通過但斷言不足」＝P2。
- NOT-EVALUABLE（本鏡未跑，原因）：
  - Playwright 類 AT（AT-961-22-1／22-2／22-5／22-6／22-7／22-8 與 11y.mock、
esearch-route.mock、
esearch-build-front.mock 所列者）與 INT 檔 	est_research_int_p1.py（AT-961-22-3／22-4／22-E-1／22-E-2／23-E-1）：本鏡未重跑真棧與 Playwright；INT 棒與主控自報 8 通過／八案全過（見 INT 證據檔），**未獨立驗證**。
  - AT-961-23-2（目錄項原語鎖）：重跑 	est_platform_neutral_paths 三個類別得 TestDirEntryPrimitivesAreAccountedFor.test_unguarded_site_census_matches_the_ledger 實測 live 1205 對帳 37；**推論**為主控派的修復棒在 repo 內 .claude/worktrees/agent-… 隔離 worktree 被掃進母體（git worktree list 可見），非 HEAD 缺陷。改以 git diff cc6164ae..HEAD -U0 -- AgentConsole/engine-bridge/app 搜新增 os.replace／rename／shutil.move 站點＝0（命中的一行是註解文字）。判 PASS（以 diff 代驗）＋原鎖 NOT-EVALUABLE，待 worktree 移除後重跑。
  - AT-961-23-5（全套 0 略過）：我的子集 1 略過（symlink TOOL-ABSENCE，與主控基線 8 略過 同源）；全套未跑。NOT-EVALUABLE。
  - AT-961-24-1（文件閘與 RTM 每列回填）：RTM 回填在 SCG-4 之後；NOT-EVALUABLE（本階段不應過）。
- Gate 類實跑：AT-961-23-3＝git diff --name-only cc6164ae..HEAD -- .claude .github AutoClaude AISDLC_SDD tools/lib 計數 0 ⇒ PASS；AT-961-23-4＝ruff 兩視角 rc=0、新增 open/read_text 無缺 encoding（唯一命中 path.open("rb") 為二進位）、tracked 檔無 CR ⇒ PASS；AT-961-23-1＝禁區差異非零（	ools/tests/test_windowsapps_guard_bash_parity.py，F-05）⇒ 依字面 FAIL、屬裁決偏離，建議勘誤。



## D 突變表（副本；`-X utf8`；測試範圍欄寫實跑的檔）
| 包 | 突變 | 結果 |
|---|---|---|
| FE（15） | failure_step snake 分支刪除 | **SURVIVED**（F-01） |
| | 確認比對加 trim／拿掉 `repoName!==""`／省略庫名不取專案名／未登記步驟名改「未知」／拆解 stale 旗標不擋／SCR 進行中不擋／TCS 未凍結不擋／豁免理由上限 +1／safeRepoHref 允許 http／分支號不截尾／分支長度 41／gh 不可用不停用 | 12 個 KILLED |
| | 空輸入也顯示錯誤；PENDING 不算進行中 | **SURVIVED**（F-03、F-04） |
| Bridge gitops（8） | `GH_TOKEN` 不剝／`TAIL_CHARS` 2001／唯讀不帶 `GIT_OPTIONAL_LOCKS`／`add -A` 不禁 worktree／分支長度 41（加 route_gate 後） | 5 KILLED |
| | `status` 不檢 args；`check_path` 不擋 `-` 起頭 | SURVIVED（等價，另有守） |
| | redact 不含百分號編碼形態 | **SURVIVED**（F-10；四檔 96 通過） |
| Bridge scr（5） | `MATRIX_GATE_FIRST` 少 RELEASE_READY／`REASON_MAX` 501／`_known_ref` 章節放行 | 3 KILLED |
| | `scr_limit` `>=`→`>` | SURVIVED（等價：`db.py:1176` 同判準） |
| | 轉態失敗補償 REJECTED→OPEN | **SURVIVED**（F-09） |
| Bridge decompose_plan（3） | 豁免空理由放行／stale 不比 sha／豁免非未覆蓋 AC 放行 | 3 KILLED |
| Bridge reconcile（3） | pending_correction 不要求 stage2／映射表去 TCS_PENDING／SPEC_FROZEN 去 SCR_OPEN | 3 KILLED |
| Bridge route（2） | PUBLIC 確認不驗／PUBLIC 軌道 A 放行 | 2 KILLED |
| Bridge outbox（3，route_exec） | 重放完成不校正 | KILLED |
| | 晚綁定不補校正 | **SURVIVED**（F-11） |
| | DbBlocked 不 return（等價：仍有 pending） | SURVIVED（等價） |
| Bridge tcs_schema（3） | 判定欄空不報／孤兒 AT 不報／機密不報 | 3 KILLED |
| backend Java（5） | FlowPolicy 不要求 stage2Frozen／BLOCKING 去 FAILED／ExecutionGuard 不查 OPEN SCR／不比 sha 不符 | 4 KILLED |
| | `STALE_STATUSES` 去 `"STALE"` | **SURVIVED**（F-12） |
| DB V19 SQL（5） | PUBLIC 僅 B 的 CHECK 拿掉／`ux_research_route_active` 改非唯一／`scr_no>=0`／kind 加 MEDIUM／`tasks_count>=-1` | 5 KILLED |
合計 52：KILLED 41／SURVIVED 11（等價 4、非等價 7）。每包是否達 5：FE 15、gitops 8、scr 5、BR-D3（decompose_plan 3＋reconcile 3＋outbox 3＋tcs 3＝12）、DB-P1 5、API-P1（ExecutionGuard 3＋FlowPolicy 2＝5）；route.py 僅 2、scaffold 0、research_route／research_scr 0——**這三處未達每包 5 個**。

## E 接縫
- 前端型別 vs `schema.d.ts`：`RouteDecisionDto.failureStep` camelCase 與 `schema.d.ts:3155` 一致；`researchErrorText` 兩形態都接（OK），測試缺口 F-01。
- 502 `failure_step` snake_case 透傳：`ResearchErrorDocs.java:99` 與 schema 描述一致；前端接得住。
- Bridge 事件型別 vs 前端描述表：Bridge `EVENT_PAYLOAD_KEYS` 新增 `research.route`（routeId、stepNo、step、status；可選 reason）與 `research.scr`（scrNo、kind、status）；前端 `RESEARCH_SSE_EVENT_TYPES`（`research.ts:854-867`）含 `research.route`、`research.scr`（亦含 P2 的 `research.delivery`）。一致。
- reason 四方鎖：`ResearchReasonsTest` 於 backend 13 類聚合通過；兩份 `*_ERRATUM_PENDING` 名單仍存在（`ResearchReasonsTest.java:60,63`）⇒ 契約／Architecture 勘誤待 RELEASE_READY 批次清空。
- D-125 三段：讀端衍生（FlowPolicy TCS_PENDING＋stage2Frozen⇒BUILD_READY，突變 KILLED）、`:reconcile` 三態（突變 KILLED）一致；freeze 後觸發段（console-api）未獨立實跑。
- D-128：重放完成校正（突變 KILLED）一致；晚綁定分支未測（F-11）。
- D-133 簽核冪等：程式（`ResearchDecompositionService.java:160-193`）與裁決一致；backend IT 聚合綠；無專屬突變。
- D-136 後繼 slug：未專驗。
- 迷你 Bridge 與真 Bridge 形狀對拍：以 `ResearchBridgeShapeTest` 聚合通過為準，未另做獨立形狀 diff。

## F 裁決偏離與勘誤核實
| TCS 位置／字面 | 實作 | 裁決 | 核實 |
|---|---|---|---|
| AT-961-23-1「禁區零差異」；§5.7 | 根層 `tools/tests/test_windowsapps_guard_bash_parity.py` 補列假 gh 夾具目錄（兩 commit，淨零行） | 無編號裁決（主控修補） | 成立，建議 §5.7 勘誤補列（F-05） |
| AT-961-10-6 後半「簽核版正式 tasks 數」 | 未實作 `imported_tasks_count` | D-143(3) | **仍未做**，F-02 |
| `DecompositionDto.prdSha256` 必填 | backend `requiredMode=REQUIRED, nullable=true` 已落地；前端收口由修復棒進行（主控自述） | D-135 | backend 半成立 |
| D-129（B1 補丁）、D-130（FE-D1 集合外兩檔追認）、D-131、D-133、D-134 | 相關測試於聚合中通過 | 同左 | **未逐一核實**勘誤條目是否仍成立；RELEASE_READY 時照裁決帳本逐條勾 |

## G 誠實劃界
- 已讀：`gitops.py` 全檔、`scr.py` 1–300、`scaffold.py` 1–230、`outbox.py` 295–358、`decompose_plan.py` 1–140 與簽核前置、`reconcile.py` 局部、`route.py` 1–200 與驗證段局部、`ResearchExecutionGuard.java`、`ResearchFlowPolicy.java` 關鍵段、V19 約束行、前端 `research.ts` 若干函式。**未讀**：`route.py` 其餘（執行、補償、重試）、`db.py` 其餘、`orchestrator.py`、`research_scr.py`、`research_route.py`、backend 其餘 Java（含 V20 種子與 ConfigCatalog）、其餘前端元件。
- 沒重跑 Playwright 與 INT 檔、沒跑 Bridge 全套、沒逐條單跑 AT（只有聚合）。
- 4 個等價突變為讀碼判讀，非證明；推論項：F-07、F-12、AT-961-23-2 的 worktree 污染成因。
- 本報告第一次續棒寫檔時被我自己的字串切割錯誤覆蓋、再由內容重建；§C 表由 `work\C_table.md` 機器生成，未受影響。

## H 殘留
- 副本 `mut\` 於交卷前刪除（先刪 node_modules junction 再刪目錄）；`work\` 保留。


---

# 二審（對 HEAD 92d50ccd；PKG-FIX-P1 修復核實）

## 二審 A 判定
- 判定：**PASS**（P1 0／P2 0）。一審的 P2×3（F-01、F-02、F-10）皆確認修好；沒有新增 P1／P2。
- 計數（二審後；F-11／F-12 由 FIX2 棒另案，依指示不再報）：**P1 0／P2 0／P3 4（F-05、F-06、F-13、F-14）／P4 2（F-07、check_path 重複防護）**。
已確認修好關閉：F-01、F-02、F-03、F-04、F-09、F-10。

## 二審 B 修法核實（逐條，皆含副本突變）
| 編號 | 修法 | 核實 | 結果 |
|---|---|---|---|
| F-10 | `gitops.py` 新增 `_char_or_escaped` 與逐字元「字面或 `%XX`」樣式（含空白切開）；`test_research_route_b.py` 新斷言 `secret.replace("_","%5F") not in out` | 突變「拿掉新增的 `re.sub` 那行（還原一審狀態）」→ route_b＋gitops 57 個測試 **1 失敗＝KILLED**。**修法有效、新斷言有鑑別力**（同一個測試在一審 HEAD 是 SURVIVED）。 | 通過 |
| F-10 衍生 | 新樣式的兩個子特性：十六進位大小寫（`%5f`）、被空白切開的編碼形態 | 突變「去掉大小寫雙形」與「去掉 `\s*` 連接」各自 57 通過＝**SURVIVED** ⇒ 這兩個特性沒有測試（產品碼本身讀起來正確）。 | **F-13（P3）**：補 `%5f` 小寫與編碼後被換行切開兩案 |
| F-02 | console-api 簽核本文加 `imported_tasks_count`（`ResearchDecompositionService.importedTasksCount`，與 confirm 匯入的是同一棵 `parsedTree`）；Bridge `decompose_plan.signoff` 驗 ≥0 整數（排除 bool、字串、浮點、None）否則 422 `invalid_request`＋`violations[].rule=imported_tasks_count_invalid`、記進簽核版 artifact JSON 與回應、冪等分支回存值；AT-961-10-6 加 `doc["imported_tasks_count"] == json_tasks == row[5]`；backend IT 斷言送出的本文值為整數 2 | Bridge 突變（artifact 不記欄位／驗證不擋負數／驗證不擋 bool／回應不帶欄位）4 個全 KILLED；backend 突變（count 恆 0／每 goal 計 1／本文不帶欄位）3 個全 KILLED。三端一致（console-api 送、Bridge 驗與記、AT 斷言）。 | 通過 |
| F-02 注意 | Bridge 側 AT-961-10-6 的相等斷言取夾具預設 `landed = tasks_count`，三者在 Bridge 測試內是同源（自證式）；「落成數＝真實 DB 正式 tasks 數」的獨立比對只在 backend IT（斷言字面 2，非對 DB 查表）。 | 見 F-14 | — |
| F-01 | `research.test.ts`、`RoutePanel.test.tsx` 各補一案，餵 snake_case `details:{failure_step}` | 突變「刪 `?? failure_step`」→ **KILLED**（2 失敗）。兩案確實餵 snake_case。 | 通過 |
| F-03 | `PublicRepoConfirm.test.tsx` 加「空輸入不顯示 alert」 | 突變「空輸入也顯示錯誤」→ KILLED | 通過 |
| F-04 | `research.test.ts` 加 `routeIsActive` 測 RUNNING／PENDING／FAILED／SUCCEEDED／空／undefined | 突變「PENDING 不算進行中」→ KILLED | 通過 |
| F-09／AT-961-12-E-2（新） | `test_research_scr.py::test_AT_961_12_E_2_…`：外環轉態被 monkeypatch 成 502 ⇒ SCR 列＝REJECTED、游標等於開 SCR 前、錯誤原樣 502、換回真實轉態後可再開（202） | 突變「補償狀態 REJECTED→OPEN」與「補償游標不還原」皆 **KILLED**（各 1 失敗）。AT 編號為「勘誤候選」，TCS 內無此條——需併入 RELEASE_READY 勘誤批次。 | 通過 |
| D-135 前端 | `lib/api/types.ts` 僅改註解 | 無行為變更 | 通過 |
- **F-13（P3）**：`gitops._char_or_escaped` 的 `%5f`（小寫十六進位）與被空白切開的編碼形態無測試（突變 SURVIVED×2，推論：產品碼本身正確）。補案。
- **F-14（P3）**：F-02 的「落成數＝正式 tasks 數」獨立相等只有 backend IT 的字面 2、沒有 `select count(*) from tasks where project…` 的實查；Bridge 測試內三數同源。TCS 要求「等於已簽核版本落成的正式 tasks 數」，建議 backend IT 改為對 DB 實查的 tasks 數相等。

## 二審 C 逐條單跑（補一審）
指令形態：Bridge `pytest <檔> -k AT_961_n_m -q -p no:cacheprovider`（副本，`BRIDGE_TEST_DSN`＋`SDD_ROOT`）；前端 `npx vitest run <檔> -t AT_961_n_m`（副本）；backend 一次 `gradlew cleanTest test --tests "*<類>.AT_961_n_m_*"` 後解析 XML 逐 AT 判定。AC-961-1～21、25 各至少 1 個 AT 單跑，**28 個 AT 全 rc=0**：

| AC | AT | 載具 | 測試檔 | rc | 摘要 |
|---|---|---|---|---|---|
| AC-961-1 | AT-961-1-1 | BE | ResearchSchemaMigrationIT | 0 | 1 methods ok |
| AC-961-2 | AT-961-2-1 | BR | test_research_route_gate.py | 0 | 42 通過, 19 deselected, 1 warning in 1.27s |
| AC-961-3 | AT-961-3-1 | BR | test_research_route_gate.py | 0 | 1 通過, 60 deselected, 1 warning in 6.90s |
| AC-961-4 | AT-961-4-1 | BR | test_research_route_exec.py | 0 | 1 通過, 24 deselected, 1 warning in 11.33s |
| AC-961-5 | AT-961-5-1 | BR | test_research_route_a.py | 0 | 2 通過, 12 deselected, 1 warning in 22.17s |
| AC-961-6 | AT-961-6-1 | BR | test_research_scaffold.py | 0 | 2 通過, 20 deselected, 1 warning in 0.62s |
| AC-961-7 | AT-961-7-1 | BR | test_research_adopt.py | 0 | 1 通過, 15 deselected, 1 warning in 2.35s |
| AC-961-8 | AT-961-8-1 | BR | test_research_gitops.py | 0 | 3 通過, 45 deselected, 1 warning in 0.41s |
| AC-961-9 | AT-961-9-1 | BR | test_research_tcs_draft.py | 0 | 3 通過, 11 deselected, 1 warning in 33.85s |
| AC-961-10 | AT-961-10-1 | BR | test_research_decompose.py | 0 | 1 通過, 19 deselected, 1 warning in 10.39s |
| AC-961-11 | AT-961-11-1 | BE | ResearchDecompositionApiIT | 0 | 1 methods ok |
| AC-961-12 | AT-961-12-1 | BR | test_research_scr.py | 0 | 1 通過, 15 deselected, 1 warning in 6.51s |
| AC-961-13 | AT-961-13-1 | BR | test_research_scr_fsm.py | 0 | 1 通過, 22 deselected, 1 warning in 14.93s |
| AC-961-14 | AT-961-14-1 | BE | ResearchRouteApiIT | 0 | 1 methods ok |
| AC-961-15 | AT-961-15-1 | BE | ResearchScrApiIT | 0 | 2 methods ok |
| AC-961-16 | AT-961-16-1 | BR | test_research_capabilities_p1.py | 0 | 1 通過, 4 deselected, 1 warning in 1.14s |
| AC-961-16 | AT-961-16-5 | FE | RouteDrawer.test.tsx | 0 | Tests  8 通過 | 16 略過 (24) |
| AC-961-16 | AT-961-16-4 | BE | ResearchRouteApiIT | 0 | 1 methods ok |
| AC-961-17 | AT-961-17-1 | FE | RouteDrawer.test.tsx | 0 | Tests  4 通過 | 20 略過 (24) |
| AC-961-18 | AT-961-18-1 | FE | BuildFrontPanel.test.tsx | 0 | Tests  4 通過 | 25 略過 (29) |
| AC-961-19 | AT-961-19-1 | FE | ResearchWorkspaceView.test.tsx | 0 | Tests  3 通過 | 49 略過 (52) |
| AC-961-20 | AT-961-20-1 | BR | test_research_reconcile.py | 0 | 2 通過, 67 deselected, 1 warning in 12.53s |
| AC-961-20 | AT-961-20-E-2 | FE | research.test.ts | 0 | Tests  1 通過 | 80 略過 (81) |
| AC-961-20 | AT-961-20-E-3 | BE | ResearchApiIT | 0 | 1 methods ok |
| AC-961-21 | AT-961-21-1 | BE | ResearchApiIT | 0 | 1 methods ok |
| AC-961-25 | AT-961-25-2 | BR | test_research_reconcile.py | 0 | 1 通過, 68 deselected, 1 warning in 6.20s |
| AC-961-25 | AT-961-25-4 | FE | BuildFrontPanel.test.tsx | 0 | Tests  3 通過 | 26 略過 (29) |
| AC-961-25 | AT-961-25-1 | BE | ResearchFlowPolicyTest | 0 | 1 methods ok |

- AC-961-22（INT 整合）：`test_research_int_p1.py` 主控親驗 8 通過 `[他包回報]`，本鏡未重跑；Playwright 三類（真棧 `research-p1-docker.stack.spec.ts`、`research-route-local.stack.spec.ts`、a11y）未跑。
- **Playwright mock spec 兩支（`research-route.mock.spec.ts`、`research-build-front.mock.spec.ts`）NOT-EVALUABLE**：在 `git archive` 副本以 `next dev`（試過 Turbopack 與 `--webpack`）啟動 webServer 皆失敗（副本以 junction 掛 node_modules，`.next/dev/fallback-build-manifest.json` ENOENT，180 秒逾時）；在主樹跑會寫入 `.next`／`test-results`，違反唯讀。待可寫的隔離環境（含真實 node_modules 複本，約 933 MB）再跑。
- AC-961-23：`git diff --name-only cc6164ae..92d50ccd -- .claude .github AutoClaude AISDLC_SDD tools/lib` 仍為 0；ruff 兩視角於 92d50ccd 重跑皆 rc=0（`All checks 通過!`）；23-2 目錄項原語鎖沿 `git diff` 代驗：`git diff 8380142a..92d50ccd -U0 -- AgentConsole/engine-bridge/app` 無 `os.replace／rename／shutil.move` 新增（實跑：新增行命中 0）。AC-961-24 RTM 回填未到階段。

## 二審 D 聚合重跑（HEAD 92d50ccd 副本）
- Bridge 研究子集 `-k "research and not int_p1" -n 6`：1272 通過／1 略過／**1 失敗＝`test_AT_961_9_6_…`**。失敗原因＝副本不是 git 倉庫（`rgs.git(parents[3],"diff","--name-only",…)` rc=129「Not a git repository」），為載具假紅；同一測試在主樹單跑 **1 通過 rc=0**。
- backend 13 類：`Test result: SUCCESS (172 個測試, 172 成功, 0 failures, 0 略過)`，BUILD SUCCESSFUL，rc=0。
- 前端全套（副本）：2352 通過／2 失敗／129 檔中 127 過；失敗＝`StudioPanel.test.tsx` 預覽 scrollIntoView（已知 N-02 負載敏感）與 `labels.test.ts`（副本缺根層 PRD 檔）。兩檔在主樹單跑 **41 通過 rc=0**。
- 主樹 `git status` 全程 0 項（唯讀紀律）。

## 二審 E 突變摘要（本輪 15 個，全在副本）
- gitops 3：還原修法 KILLED；大小寫 SURVIVED；空白切開 SURVIVED。
- decompose_plan 4：全 KILLED。
- scr 2：全 KILLED。
- 前端 3：全 KILLED。
- backend Java 3：全 KILLED。
- 累計（一審 52＋二審 15）：KILLED 56／SURVIVED 11（F-01、F-03、F-04、F-09、F-10 已由修法轉 KILLED；現存 SURVIVED 為 F-11、F-12、F-13×2＋4 個等價）。

## 二審 G 未清與劃界
- 未清：F-05、F-06（P3，待 RELEASE_READY 勘誤／RTM 回填）、F-13、F-14（P3）；F-11、F-12 由 FIX2 棒處理，本鏡不再報。
- 勘誤候選：AT-961-12-E-2（新增 AT 編號）、AT-961-10-6 的 `imported_tasks_count` 條文、`imported_tasks_count_invalid` 加進 reason／violations 規則表、F-05。
- 本鏡仍未讀 `route.py` 200 行後、`db.py`、`orchestrator.py`、`research_scr.py`、`research_route.py`、V20／ConfigCatalog；Playwright 全部未獨立驗證。
- 殘留：副本 `mut\` 於交卷前刪除（先刪 node_modules junction 再刪目錄）；`work\` 保留；已終止我啟動的 Next dev 行程（現 node 行程 0）。
