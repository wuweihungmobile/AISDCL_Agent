# SCG-0～3 規格階段審查報告：鍵 `agentconsole-si-flow-visibility`（Console 半，第一波）

- 審查日期：2026-11-11；審查者：獨立審查棒（未參與撰寫）；輸入快照：HEAD `e1ad0ac0` 加工作樹未提交的規格檔。
- 結論：**CONDITIONAL**（無 P1；P2 共 7 筆，其中 2 筆的修改點在根層、5 筆在 Console；全數修畢並二審後方可凍結）。

## 1. 審查範圍

| 類別 | 檔案 |
|---|---|
| 被審 | `AgentConsole/docs/03_testing/contracts/TCS-SiFlowVisibility-20261111.md`（1116 行）；`docs/01_requirements/Agent_ConsoleUI_PRD.md` §0.12（215～232 行）；`AgentConsole/docs/02_architecture/Architecture.md` §5.7（534）、§9.4 一列（1028）、§10.5（1173）、§12.1 L-SI-3（2208）；`AgentConsole/docs/06_quality/RTM.md` §2.16（513）；`AgentConsole/docs/04_planning/Implementation_Plan.md` 454 行 |
| 對照 | 根層 `docs/03_testing/contracts/TCS-SelfImproving-P7-20261111.md`（§2.1、§2.2、附錄 A）；`REVIEW_COMMON.md` 裁決 1～11；兩份 SA 交卷 |
| 現況查證 | `SiKeyNames.java`、`docker-compose.yml`、`test_si_deploy_config.py`、`playwright.config.ts` 與既有 `.stack.ts` 檔、`a11y.mock.spec.ts` 寬度常數、`SiView.tsx`、`AgentConsole/build/reports/fsm` 與根層 `build/reports/fsm` 的凍結紀錄 |

未實跑任何測試；未改任何規格檔。

## 2. 逐項結論

1. **AC／AT 可測性與一致性：通過（含下列發現）。** AT 定義 110（`^- \*\*AT-966-` 計數）、驗收字樣 110、§1 映射列 110、§3 分類 19＋10＋73＋8＝110、命名文法與 `E` 負控 22 皆吻合；17 條 AC 皆至少一條 AT。測試檔落點沿既有慣例（Bridge `tests/test_si_*.py`、backend `adapter/in/web/*IT`、前端 `components/domain/si/*.test.tsx`）；`self-improving-flow-docker.stack.ts` 的 `.stack.ts` 後綴合於既有慣例（`self-improving-docker.stack.ts`、`p9-w7-docker.stack.ts` 等，`playwright.config.ts` 的 `testMatch` 為 `*.spec.ts`，stack 檔以顯式路徑執行）。Given／When／Then 大多可機械判定；C-06 的欄名風格矛盾與 C-07 的金絲雀除外。
2. **裁決落實：1、2、3、4、5、9、10 符合；8 部分不符；11 不符。**
   - 1：AC-966-1／2 只讀、無簽章（W-F1、AT-966-1-6）。2、3：Console 只顯示 `push`，不依賴 `PUSH-*` 碼集合，無推送按鈕（AT-966-12-6）；但列舉值不齊（C-03）。
   - 4：全檔無寫入端點、無第二波按鈕；「看待入帳清單」只是捲動聚焦（AT-966-12-4）；唯一與裁決 4 相抵的是夾具把 `NO-HELDOUT` 寫成「等無人運轉凍結」（C-11）。
   - 5：新鮮度＝`2×hb+5` 嚴格大於，三種缺席各有畫面（AT-966-11-5～7）；唯顯示的相對時間以讀取時為基準（C-08）。
   - 8：Console 另持有「案例數低於下限，驗證必判『無法評估』」整句與沙盒保底句（C-05、C-02）；未知碼保底本身合規。
   - 9：`console-writes` 十一鍵不動、前端以稽核編號結合、VIEWER 可看 diff 與本文，皆已落實並有 AT（5-7、13-x、14-E-1）。
   - 10：Console 端沒有任何既有 AT 提及 `AUTOSDD_SI_PATROL_OFF`（對 `AgentConsole` 搜尋僅命中本鍵新增文字），OFF 快照不與既有已發布 AT 衝突；Console 以 AT-966-11-4 處理。
   - 11：Console TCS §5.1 引用 `patrol.golden.json`、`detail.golden.json`，但**根層 TCS 與 PRD 全文不含黃金樣本路徑**（對 `*P7*` 檔搜尋 `golden` 命中 0），無處可引（C-01）。
3. **畫面與文案：大致合格，另有改善項。** 詳情五分頁、diff 的符號＋實線／虛線邊框＋讀屏前綴、評估集只露六欄、沙盒／驗證三步、時間線、「下一步」一句話、三種缺席畫面、超大 patch 視窗化、VIEWER 與 ADMIN 一視同仁、50 組垃圾輸入的 `null`／`NaN` 鎖，規格都有對應 AT。需改處見 C-08（新鮮度基準）、C-09（技術詞彙）、C-02／C-05（白話來源）。
4. **既有已發布 AT：§4.1 同步清單合理，未發現遺漏的必然失效項。** 已核 `test_si_deploy_config.py` 的 `audit_bind_problems`（只禁其他「可寫」bind）與 `si_mount_problems`（只看 `/repo` 之下的 target）：`/si-report` 唯讀、不在 `/repo` 下，既有兩個檢查函式不會誤判。`SiKeyNames.camelKeys` 已套用於整棵樹所有層級（`SiKeyNames.java:18`），故 backend 對 `detail` 與 `patrol` 零邏輯改動的說法屬實。**refreeze 清單有誤**，見第 4 節與 C-12。
5. **與根層介面一致性：** 發現 C-01～C-06、C-13；根層已提供但 Console 未納入的欄位見 C-10。
6. **部署：** `create_host_path: false`、長語法、`read_only`、來源以 `console_report` 結尾、與稽核目錄互異，皆有 AT（2-1～2-3、2-E-1 的 `docker compose config`）；未設環境變數只影響 `/si/patrol`（2-5）。缺口：首次升級與長駐棧升級的步驟順序與失敗表徵寫得不夠（C-07 之外的 C-14）。
7. **測試策略：** 分工足以證明 AC（Bridge 單元＋整合、backend IT、vitest、mock E2E、拋棄式全棧）。只能目視者僅 V7（文案白話程度）與 V1／V2／V3 的真機項，皆已標為非 AT 並要求如實標「未驗」。風險點：AT-966-17-1 的 rename 覆寫在 Docker Desktop 的可見性由 V3 實測，規格已寫退路。

## 3. 發現表

| 編號 | 嚴重度 | 位置 | 問題 | 建議修法 | target |
|---|---|---|---|---|---|
| C-01 | P2 | 根層 TCS-P7 §3／§2；Console TCS §0.2、§5.1、SCG-4 第 3 項、§7.2-2(e)、增量追溯表末列 | 裁決 11 要求「黃金樣本路徑由根層 TCS 定義、Console 引用同一路徑」。根層 TCS 只有夾具建構器（`tools/tests/_selfimproving_p7_fixtures.py`），沒有任何黃金檔路徑；Console 只好寫裸檔名 `patrol.golden.json`／`detail.golden.json`，並說「主控複製、sha256 先驗」，驗收條件無從執行 | 根層 TCS 新增小節定義兩個黃金檔的 repo 內路徑與由哪個 AT 產生／比對（`export` 位元組＋快照位元組各一）；Console TCS 三處改寫為同一路徑並把 sha256 比對寫成可執行指令。路徑定案前 AT-966-1-1、4-1、4-3 的第二列不可驗 | root（Console 隨後引用） |
| C-02 | P2 | 根層 TCS-P7 §2.1 `sandbox` 與 AT-747-5-1；Console AT-966-9-3、5-8、PRD §0.12-3 | 裁決 8 明列「含沙盒失敗碼」都要同帶白話，但根層 `sandbox` 只有 `failCode`，鍵集被 AT-747-5-1 釘為恰六鍵。Console 因此把「（主機沒有提供白話說明）」當成**常態**顯示，而 PRD 又寫「原因碼一律有對照文字」，兩者矛盾 | 根層 `sandbox` 增 `failText`（`nextstep.reason(failCode).text`，無失敗為 null）並同步 AT-747-5-1 與附錄 A 涵蓋沙盒碼；Console 的 C-3、AT-966-9-3、5-8 改為「有 `failText` 則逐字、缺席才用保底句」 | root＋console |
| C-03 | P2 | Console §0.2 C-5「推送狀態」、AT-966-5-9、12-5（「八種狀態」）；根層 §2.2 | Console 的狀態表是設計稿舊值（`idle／running／ok／failed／skipped`），根層定稿為 `off／idle／pending／waiting-login／running／ok／failed／blocked`。`pending`、`waiting-login`、`blocked`、`off` 四個合法值在 Console 會被顯示成「未知的推送狀態」，而 `waiting-login` 正是推送最常見的真實狀態；`skipped` 反而是根層不會產生的值。AT-966-12-5 的「八份」也不是根層八態。`idle` 且 `ahead>0` 的案例根層不會產生（有領先提交時是 pending／waiting-login／blocked） | C-5 與 `pushView` 改成根層八態各一個固定標籤（`pending`＝等待推送、`waiting-login`＝等使用者登入、`blocked`＝被擋住〔原因看主機的白話〕、`off`＝已關閉），`skipped` 改列未知值測試案例；AT-966-5-9、12-5 的夾具逐態對齊根層 §2.2，並新增 `enabled:true`＋`state:"off"` 與 `blocked` 帶 `code`／`text` 案例 | console |
| C-04 | P2 | Console §0.2 C-5「運轉目的」、AT-966-12-3；根層 §2.2、AT-747-11-1 | 根層 W1 的 `purpose` 為 `scheduled／console／manual`，Console 表缺 `manual`（會顯示「未知值『manual』」）；`freeze／revise／propose` 在 W1 不會出現，卻當成已知標籤，與本鍵「第二波不在範圍」相抵 | 加 `manual`＝「手動」；`freeze／revise／propose` 移出已知表（第二波再加，走勘誤），保留在未知值測試中 | console |
| C-05 | P2 | Console W-F9、AT-966-5-8、9-1(c)、PRD §0.12-3；根層 §2.1 `heldout.neNote` | 根層已提供 `heldout.neNote`（belowMin 時的白話），Console 卻忽略它並在前端寫死整句「案例數低於下限，驗證必判『無法評估』」，等於在 Console 另持有一份原因白話，違反裁決 8「單一真相源在根層、Console 只做未知碼保底」，也會與根層文字漂移 | belowMin 為 true 時顯示 `neNote`（逐字）；Console 固定句只在 `neNote` 缺席或空時當保底；AT-966-9-1(c)、5-8 對應改寫。`digest8` 仍不顯示（AT-966-9-2 金絲雀的 `digest` 鍵維持） | console |
| C-06 | P2 | AT-966-5-7、11-E-2、12-3、12-E-1、13-1、13-2、13-E-1 的 Given | 前端 AT 的 Given 一半寫 snake_case（`audit_ref`、`started_at`、`wall_due_at`、`generated_at`、`schema_rev`），而前端實際收到的是 backend 轉過的 camelCase（C-2、§5.1 的 `PATROL()` 基準即 camelCase）。同檔兩種寫法使實作者無從判斷 `joinHostRejections` 該讀 `audit_ref` 還是 `auditRef`，照字面寫的測試會與 `PATROL()` 夾具互相打架 | 凡前端 AT 的 Given 一律改用 C-2 的 camelCase 並以 `PATROL(over)` 表達；snake_case 只留在 Bridge 與 backend 層 AT；W-F10 的「`ingest[].audit_ref`」改為「`ingest[].auditRef`（Bridge 層為 `audit_ref`）」 | console |
| C-07 | P2 | AT-966-17-2、§5.7、NFR-FV-9 | 該 AT 要以「評估集目錄中任一檔案的首行字串」當金絲雀，但評估集住 `~/.autosdd/selfimproving/heldout/`（根層 TCS 的 AT-747-4-E-2 亦同），而 compose 只把 `tools`、`docs/06_quality`、`.git` 的幾條與稽核目錄掛進 Bridge 容器，評估集根本不在容器內，且根層 `propdetail` 被 AST 禁止讀它。結果：(a) 要取金絲雀就得讀真 SI 家目錄，直接違反本檔 NFR-FV-9 與 §5.7「不讀真 SI 家目錄」；(b) 即使取到，斷言也恆為真，**變不成紅燈**（預期突變「Bridge 對 `detail` 做過濾」也驗不到它） | 改為在全棧自帶的拋棄式 `AUTOSDD_SI_DIR` 內預先放一份帶唯一金絲雀字串的假評估集目錄，斷言 DOM 與 `detail` 回應皆不含；並在 AT 內明寫「容器讀不到評估集，零外洩的保證主體是根層 AT-747-4-E-2，本 AT 驗的是 Console 端不自行渲染未知鍵」。保留的真提案比對只讀 repo 內追蹤檔 | console |
| C-08 | P3 | W-F5、AT-966-11-2、11-1、W-F12 | 相對時間以 `readAt − generated_at` 計算且頁面不輪詢，所以頁面開著放兩小時，卡片仍寫「上次心跳：3 分鐘前」、永不轉為過時，容易讓人誤信「巡邏正常」（掌舵者最在意的情境）。已有「資料更新於 <readAt>」但與「N 分鐘前」並列時意思不清 | 加上「（資料讀取時）」字樣於相對時間後，或以 `readAt` 加上「自讀取起經過的時間」（用 query 的 `dataUpdatedAt`）補算，過了 2×hb＋5 即可在不輪詢下轉警示；擇一並補 AT | console |
| C-09 | P3 | AT-966-13-4（「連不上 Bridge」）、9-4（`carrierProof` 原樣）、9-3（`failCode` 等寬）、「探針數」「沙盒」、§5.1 名詞表只增三列 | 國高中程度目標下，「Bridge」「carrierProof」「沙盒」「探針」「載具」不經說明就出現；`carrierProof` 無標籤只顯示值 | 「連不上 Bridge」改「連不上後端服務」；`carrierProof` 加標籤與一句說明或不顯示（它對掌舵者沒有決策價值）；名詞表補「沙盒」「探針」；可讀性鎖（AT-966-15-2）把這些詞納入檢查 | console |
| C-10 | P3 | Console §0.2 C-3、W-F4、AT-966-4-3、7.2-2 | C-3 寫「六欄」，根層 `detail` 實為八欄（`patch、body、sourceObs、heldout、sandbox、verify、next、timeline`）且 `heldout` 另有 `digest8`、`neNote`；根層特別註記「Console 端 SA 須對齊」。Console 未把它們列進契約，也沒寫為何不用 `sourceObs`（來源觀察的內容）與 `timeline`（免打 `GET /issues/{id}`），造成 AT-966-8-4「來源不在已載入頁」的降級體驗與多一次請求 | C-3 逐欄列齊八欄；在 §7.1 明記「採用／不採用 `sourceObs`、`timeline` 的理由」。建議採用 `sourceObs` 在「提案本文」顯示來源摘要（無需額外請求，修掉 8-4 的找不到情境），`timeline` 可擇一（改用則 AT-966-10-x 需改寫，不改也可，但要寫明） | console |
| C-11 | P3 | AT-966-12-1、§5.1 `PATROL` 基準 steps；根層附錄 A.2 | 夾具把 `NO-HELDOUT` 寫成 `who:"無人運轉"`、`text:"還沒有評估集，等無人運轉凍結"`，根層為 `who:"主機管理者"`、「需有人用 `heldout-freeze`，巡邏器不會自己湊」。夾具暗示自動凍結存在，與裁決 4（自動凍結屬第二波）相抵，也可能被實作者抄進說明 | 夾具改為根層字樣（`who:"主機管理者"`）；AT-966-9-1(a) 的說明句與每頁說明同步檢查不暗示自動凍結 | console |
| C-12 | P3 | Console TCS §4.1 末段「需要 spec-refreeze 的鍵」 | 清單寫 Architecture.md 有 11 把持有者要重凍。逐把比對各鍵最後一筆摘要與 HEAD 檔的 sha256：**只有 `agentconsole-si-schedule` 的 Architecture 摘要仍等於 HEAD**，其餘 10 把早已不等於 HEAD（先前輪次改 Architecture 時未重凍），重凍它們只是蓋新章、並非「因本鍵而失效」。PRD 8 把皆等於 HEAD，清單正確。另確認 Implementation_Plan.md、RTM.md 不被任何 Console 鍵持有；根層 `build/reports/fsm` 沒有任何鍵持有 Console 的 PRD／Architecture | 清單改為本報告第 4 節；並把判準寫成「最後一筆摘要等於 HEAD 者才要 refreeze」 | console |
| C-13 | P3 | 根層 TCS-P7 §2.1 末段 | 註記稱「backend `SiKeyNames` 深層對映需加」，但 `SiKeyNames.camelKeys` 已套用整棵樹所有層級（`SiKeyNames.java:18`），backend 不需要任何改動；此話會誘使實作者去改 Console backend 並越出 Console TCS §5.7 的範圍 | 根層刪該句，或改為「backend 已深層對映，只需補測試」 | root |
| C-14 | P3 | Console §6.2 V1、README／`.env.example` 要求（AT-966-2-4）、決策 §7.1-9 | `create_host_path: false` 使 `docker compose up` 在目錄不存在時直接失敗；規格只說「首次升級要先建目錄」，未寫順序：重建 engine-bridge 映像（新 `si_report.py`）、backend、frontend 的先後、`console_report` 在哪一步由誰建（根層巡邏第一次心跳才會寫檔）、失敗時看到什麼訊息、退回舊 compose 的方式。AT-966-2-4 只驗文字存在 | README 的小節與 V1 加上完整升級序列（建目錄→重建三個映像→`up -d`→驗 `/si/patrol` 回 503 `report_missing` 再等第一個心跳）與一行失敗表徵；可請根層在 `sched arm` 順手建立該目錄 | console（根層可選） |
| C-15 | P4 | Console TCS 檔頭、§0.2、增量追溯表末列、§7.2-2(e) | 多處寫「根層 TCS 檔名以根層棒交卷為準、凍結前由主控填入」，現已定案為 `TCS-SelfImproving-P7-20261111.md`；此類「待填」字樣在凍結時不得殘留 | 直接填入實際檔名，刪除「待填」語句 | console |
| C-16 | P4 | AT-966-16-2 寬度 1440／1000／600；V7 寬度 375 | AT 沿 `RESEARCH_WIDTHS`（1440／1000／600，合既有慣例），V7 卻要 375，兩者不同源，PRD 的「三寬」也未列數值 | 統一寫明三寬數值（建議 AT 沿用 600，V7 另加 375 為手機補充並註明非 AT） | console |

## 4. 需 refreeze 的鍵（核對後版本）

查證法：對各鍵狀態檔取該文件最後一筆 `spec_doc_digests` 摘要，與 `git show HEAD:<檔>` 的 SHA-256 比對；請主控凍結前仍以各鍵 `show --json` 的 `frozen_stages[-1].spec_doc_digests` 為準。

**Console 鍵（state dir `AgentConsole/build/reports/fsm`，`--root` 取 monorepo 根）**

| 重記的 `--doc` | 需重凍的鍵 |
|---|---|
| `docs/01_requirements/Agent_ConsoleUI_PRD.md` | `agentconsole-console-ux-sort-help`、`agentconsole-exec-monitor-entry`、`agentconsole-fsm-trail`、`agentconsole-nav-consolidation`、`agentconsole-research-to-prd-p0`、`agentconsole-research-to-prd-p1`、`agentconsole-research-to-prd-p2`、`agentconsole-si-schedule`（共 8，摘要皆等於 HEAD） |
| `AgentConsole/docs/02_architecture/Architecture.md` | `agentconsole-si-schedule`（共 1；與上列 PRD 同一次指令併記兩個 `--doc`） |

- 不需重凍：Architecture 的其餘 10 把持有者（`console-ux-sort-help`、`exec-monitor-entry`、`fsm-trail`、`nav-consolidation`、`research-to-prd-p0／p1／p2`、`si-decide`、`si-decide-dedupe`、`si-mirror`）摘要在本鍵之前就已不等於 HEAD，與本鍵無關（Console TCS 寫 11 把為誤）。
- 不需重凍：`Implementation_Plan.md`、`RTM.md` 無任何鍵持有；`agentconsole-research-registry`、`page-help`、`issue-center`、`sysadmin-backup` 不持有這兩檔。
- 根層鍵（`build/reports/fsm`）：沒有任何鍵持有 Console PRD／Architecture／Implementation_Plan／RTM，不需動。Console 鍵持有的根層檔（`SelfImproving_PRD.md`：`si-mirror`、`si-decide`、`si-decide-dedupe`）摘要早已不等於 HEAD，根層 P7 的修改不影響它們。
- 若 C-01～C-07 的修訂再動到上列檔，本表不變；本鍵自身（`agentconsole-si-flow-visibility`）依常規流程凍結 Stage-1（PRD、Architecture）與 Stage-2（本 TCS）。

## 5. 結論

**CONDITIONAL。** 規格骨架紮實：AT 數量三處一致、AC 全覆蓋、既有 console-writes 十一鍵與 argv 白名單零改動、無偷渡寫入功能、部署鎖與唯讀鎖設計到位。但有 7 筆 P2（C-01～C-07）涉及與根層契約的欄位／列舉不一致、白話來源違反裁決 8、黃金樣本缺失（裁決 11）、AT 內部欄名矛盾與一條無法變紅且違反 hermetic 的 AT；依門檻不得判 PASS。建議流程：根層棒先補 C-01、C-02（並順手 C-13）→ Console 棒修 C-03～C-07 與 P3 → 二審只重核這些列與 §4 的 refreeze 清單。

---

# 二審（2026-11-11；沿用一審獨立視角，只讀現行檔案自行驗證，不採信修訂者回報）

結論：**CONDITIONAL**（無 P1、無 P2；剩 P3 四筆、P4 一筆，皆為殘留矛盾或過度宣稱，修畢即可 PASS，不需再全面審查）。

## S1. 一審 target=console 發現的逐條驗證

| 編號 | 驗證結果 | 證據（現行檔） |
|---|---|---|
| C-03 推送狀態 | 已修正 | W-F7、C-5：Console 不建推送標籤表，顯示句＝`push.text`，`state` 只決定樣式與是否已知；AT-966-5-3 已知集合為根層八態，`skipped` 列為未知；AT-966-5-9／12-5 夾具逐態取自根層附錄 A.4／A.4b，含 `PUSH-NOT-RECORDED`、`PUSH-RECORD-MISMATCH`、`PUSH-LEDGER-RULE` 且明寫「不需特例」，預期突變含「對新碼寫特例」 |
| C-04 運轉目的 | 已修正 | W-F7：三值 `scheduled／console／manual`；`freeze／revise／propose` 與 `runs.queued` 明定不當已知值、不渲染（AT-966-12-3 驗） |
| C-05 `neNote` | 已修正 | W-F9、AT-966-5-8、9-1：`belowMin` 時逐字顯示 `neNote`，缺席才用保底句；`digest8` 不顯示且納入金絲雀 |
| C-06 欄名風格 | 已修正 | §5.1 `PATROL`／`DETAIL` 基準全 camelCase；AT-966-5-7、11-E-2、12-3、12-7、13-1 的 Given 皆 camelCase；AT-966-5-7 另鎖「snake_case 鍵視為無對應項」 |
| C-07 AT-966-17-2 | **部分修正** | 不再讀真家目錄、改用拋棄式 `AUTOSDD_SI_DIR` 內的合成哨兵，hermetic 違規已解；但「任何一層讀取該目錄並輸出，哨兵就會出現」的宣稱不成立，見 C-19 |
| C-08 新鮮度基準 | 已修正 | W-F5 改為 `(readAt−generatedAt)＋(現在−dataUpdatedAt)` 並每分鐘本地重算（`useMinuteTick`，不發請求）；AT-966-5-1（`receivedAtMs`／`nowMs` 注入）、11-2、11-3 覆蓋「放著不動自動轉過時」；PRD §0.12-4、-7 與 Architecture §5.7 同步 |
| C-09 技術詞 | 已修正 | AT-966-13-4 改「連不上後端服務」；沙盒／探針只准括號形態；`carrierProof` 改為「驗證用的測量工具自我檢查：通過／沒通過／量不到」；AT-966-15-2 加禁用詞表（`Bridge`、`carrierProof`、`probe`、`sandbox`、`digest`、`schema`、`payload`、`HMAC`）；名詞表擴為五列 |
| C-10 欄位採用 | 已修正 | C-3 列齊八欄、W-F14 逐欄採用／不採用附理由；時間線與來源觀察改取 `detail.timeline`、`detail.sourceObs`，AT-966-6-3、10-1、14-1 全程斷言零 `/api/v1/issues/` 請求，AT-966-8-5、10-3 新增 |
| C-11 夾具 | 已修正 | AT-966-12-1 改為 `who:"主機管理者"`、「巡邏器不會自己湊」，與根層附錄 A.2 一致，且斷言不得出現暗示自動凍結的句子；AT-966-15-1 加禁字 |
| C-12 refreeze | 已修正 | §4.1 末段與本報告第 4 節一致（PRD 8 把、Architecture 僅 `agentconsole-si-schedule`）；我重跑比對，HEAD 仍為 `e1ad0ac0`，結果不變 |
| C-14 升級序列 | 已修正 | D2、V1 寫齊：建目錄（雙 shell）→重建三映像→啟動→驗證→失敗表徵→退回；AT-966-2-4 機械檢查順序；PRD §0.12-8 同步 |
| C-15 待填字樣 | 已修正 | 檔頭、增量追溯表、§7.2 皆填入 `TCS-SelfImproving-P7-20261111.md` 與黃金樣本路徑 |
| C-16 寬度 | 已修正 | NFR-FV-6、AT-966-16-2 取 `RESEARCH_WIDTHS`（現值 1440／1000／600），V7 的 375 明標為非 AT 補充；唯 AT-966-16-2 的實作前提見 C-18 |

## S2. 與根層現行 TCS-P7（§2、§3、附錄 A）及 `SA_ROOT_HANDBACK.md` 的介面一致性

逐欄核對結果：**無不一致**。

- `detail` 八欄、`heldout` 八鍵（`digest8` 不顯示）、`sandbox.failText`、`verify.carrierProof` 為 bool｜null、`ne` 新碼項帶 `text`、`timeline` 五鍵、`sourceObs` 含 `missing:true`：C-3 與根層 §2.1 逐項相符（可空性亦同）。
- 快照：`schedule`（OFF 時 null）、`runs.waiting[]`、`runs.queued` 恆空、`push` 十鍵、`push.state` 八態與 `code`／`text` 恆非空、`push.retry`、頂層 `truncated`：C-1 與根層 §2.2 相符；`runs.live[].purpose` 三值、`ingest[].status`、`permanent` 相符；`AUDIT-REF-REUSED` 為 `permanent:true`（根層附錄 A.1）與 AT-966-13-2 一致。
- 黃金樣本路徑 `tools/tests/fixtures/selfimproving/p7/{patrol,detail}.golden.json`：Console §0.2、§5.1、增量追溯表、AT-966-1-1／4-1／4-3 與根層 §3、AT-790-5-1 一致；三側複本以先行測試逐位元組比對，機械可判。
- Console 側不自建任何原因碼或推送狀態對照：W-F7、C-5、§7.1-10 明定；僅持有三組小列舉標籤（運轉目的三值、驗證結果三值、入帳狀態兩值）與保底句，三組皆為根層未提供白話欄的固定小集合，可接受。根層新增碼（`PUSH-NOT-RECORDED`、`PUSH-RECORD-MISMATCH`、`PUSH-LEDGER-RULE`、`COMMIT-LEFTOVER`、`COMMIT-RECORD-FAILED`）Console 皆不需認得（AT-966-5-9、12-2 以夾具證明走同一條路徑）；根層正在加入的 `COMMIT-LEDGER-RULE` 同理，不需 Console 改動。
- `read_at`（Bridge）→`readAt`（backend、前端）：C-1、C-2、AT-966-1-1、3-2 一致，且 `SiKeyNames.camel("read_at")` 的行為與規格相符。

## S3. 修訂引入的新矛盾、計數與映射

- 計數：AT 定義 112、驗收字樣 112、§1 映射列 112、§3 分類 19＋10＋75＋8＝112；RTM §2.16（131＝1＋1＋17＋112）、Implementation_Plan、TCS 第 45 行皆為 112，無殘留 110。
- 映射：新增 AT-966-8-5、12-7 皆在 §1 與 §3 的分項計數中（AC-966-8 為 6、AC-966-12 為 9）；每個 AC 內數字序未超過 9。
- 殘留矛盾與過度宣稱見下表（新發現）。

## S4. 新發現（編號接續）

| 編號 | 嚴重度 | 位置 | 問題 | 建議修法 | target |
|---|---|---|---|---|---|
| C-17 | P3 | §4.1 第 1012、1014 列；§5.6 | 修訂後殘留的舊敘述：(a) §4.1 與 §5.6 仍要在 `tests/helpers/si.tsx` 加 `issue` 端點，但本鍵已不打議題端點；(b) §4.1 寫名詞表「加三個名詞列」，AT-966-15-1 要求五列（巡邏快照、評估集、下一步、沙盒、探針）；(c) §5.6 的假計時器例外只列 AT-966-11-E-1(d) 與 11-1，但 AT-966-11-2、11-3 也用假計時器 | 三處同步改正：刪 `issue` 端點、列數改五、例外清單補 11-2、11-3 | console |
| C-18 | P3 | AT-966-16-2、§4.1、§5.7 | AT 要求寬度與 `a11y.mock.spec.ts` 同源，而 `RESEARCH_WIDTHS` 在 `a11y.mock.spec.ts:177` 與 `research-deliver.mock.spec.ts:20` 各自宣告、都未匯出，所以「搬到 `tests/e2e/a11y.ts`」是必然動作；這會改兩個既有測試檔，卻不在 §4.1 的同步清單與 §5.7 的允許集合內，開發 agent 會因越權而卡住 | §4.1 補一列（`a11y.ts` 匯出常數、兩支既有 spec 改為引用，只動宣告不動斷言），並納入 §5.7 允許集合 | console |
| C-19 | P3 | AT-966-17-2（「誠實劃界」與預期突變） | 容器掛載只有 `tools`、`docs/06_quality`、`.git` 數條與稽核、巡邏回報兩個目錄；拋棄式 `AUTOSDD_SI_DIR` 的 held-out 目錄**不在容器內**，根層 CLI 讀不到它。所以「任何一層讀取該目錄並輸出，哨兵就會出現」不成立，預期突變「根層把評估集目錄內容放進 `heldout`」在此棧也無法觸發；AT 實際只能證明「回應與 DOM 不含哨兵」（恆真）。AT-966-9-2 在 vitest 層是真的能紅（`Object.entries` 突變），無此問題 | 刪去「可被造成紅燈」的宣稱與該預期突變，改明寫「本 AT 在全棧層是冒煙檢查，零外洩的保證主體是根層 AT-747-4-E-2 與 AT-966-9-2」；或另設一條不依賴容器可見性的突變（例如以 fake_si 回傳帶哨兵未知鍵的 `heldout`，驗 Bridge、backend、前端三層皆不洩漏） | console |
| C-20 | P3 | §7.2 第 4 點 | 引用 `SA_CONSOLE_HANDBACK.md〈一審處置〉`——那是 session 暫存目錄的檔，不在 repo，凍結後他機讀不到（違反「他機可重現」）；同節「一審修訂後狀態」等流程用語也不宜留在凍結檔 | 刪第 4 點，或改引本報告 `AgentConsole/docs/06_quality/SCG0-REVIEW-SiFlowVisibility-20261111.md` | console |
| C-21 | P4 | AT-966-3-2；AT-966-5-9 與 12-7；W-F14；AC-966-12 摘要；§5.1 夾具檔、AT-966-4-1 | 小處不一致：(a) AT-966-3-2 的 Given 未涵蓋新增的 `schedule.last_skip`、`runs.waiting`、`push.retry`／`tick_at`，且「`readAt` 恆等」的說法已過時（現為 `read_at`→`readAt`）；(b) `schedule` 為 null 時的句子，AT-966-5-9 寫「巡邏已暫停或這份回報沒有排程資訊」，AT-966-12-7(d) 寫「巡邏已暫停，沒有排程資訊」，且未規定 `schedule:null` 而 `off:false` 時的畫面；(c) W-F14 稱 `push.retry` 採用為補充顯示，AT-966-5-9 卻寫「`retry` 不另加句子」；(d) FRD-lite 的 AC-966-12 摘要未提「為什麼沒有啟動運轉」；(e) `patrol-stale.json` 等前端夾具檔以 `generated_at` 命名描述，而前端夾具應為 camelCase；黃金樣本複本是 snake_case，「轉 camelCase」由誰實作（測試輔助函式的規則須等同 `SiKeyNames`）未指明；(f) 黃金 `detail` 樣本是整個 `items[0]`，AT-966-4-1、4-3 只說「第二列＝黃金樣本複本」，未說明 `FAKE_CLI`／`MINI` 回傳整個 `items[0]` | 逐點補一句即可，不改設計 | console |

## S5. 二審結論

**CONDITIONAL**。一審的 7 筆 P2 與 target=console 的全部 P3／P4 皆已修正（C-07 部分修正，餘項降為 C-19），根層 C-01、C-02、C-13 在根層現行檔確認已落實，雙邊介面逐欄一致，Console 不自建原因碼與推送狀態對照。無 P1、無 P2；剩 P3 四筆（C-17～C-20）與 P4 一筆（C-21）。依門檻「有 P1／P2 才不得判 PASS」，這些殘留不阻擋凍結，但 C-17～C-20 屬凍結前應一次改正的文字層問題（否則凍結後只能走勘誤），建議主控要求修訂者一次改完後以抽查確認即可，不需再做全面審查。

**refreeze 清單**：與第 4 節相同，未因第二輪修訂而變；Console 鍵 PRD 8 把（console-ux-sort-help、exec-monitor-entry、fsm-trail、nav-consolidation、research-to-prd-p0／p1／p2、si-schedule）、Architecture 僅 si-schedule；根層鍵與其他 Console 鍵不需動（HEAD 仍為 `e1ad0ac0`，現查摘要比對結果不變）。

---

# 三審（2026-11-11；範圍僅限二審 C-17～C-21；讀現行檔案自行驗證）

結論：**CONDITIONAL**（無 P1、無 P2；C-17～C-21 全數修正；本輪修訂引入 1 筆 P3、1 筆 P4 的殘留，皆文字層）。

## T1. C-17～C-21 驗證

| 編號 | 結果 | 證據 |
|---|---|---|
| C-17 | 已修正 | §4.1 第 1019 行明寫「不加 `issue` 端點」；名詞表為五列（AT-966-15-1，§4.1 同步）；§5.6 假計時器例外已含 AT-966-11-2、11-3（1049 行） |
| C-18 | 已修正 | §4.1 第 1020 行新增列：`a11y.ts` 匯出 `RESEARCH_WIDTHS`、`a11y.mock.spec.ts`／`research-deliver.mock.spec.ts` 改為引用，註明只動常數宣告；§5.7（1053 行）同步 |
| C-19 | 已修正 | AT-966-17-2 明寫為全棧冒煙檢查、不宣稱可變紅，並指向根層 AT-747-4-E-2、新 AT-966-4-6、AT-966-9-2；AT-966-4-6 以合成哨兵驗證多帶鍵（含 `heldout.cases`、`patch.raw`、`verify.reasons[0].trace`、`timeline[0].pid` 等）在回應任何位置都不存在，並有「拿掉白名單即紅」「漏列 `neNote`／`digest8`／`kind` 亦紅」的突變；W-F4、D1、NFR-FV-4、Architecture §5.7／§10.5、§3.1 分類皆同步 |
| C-20 | 已修正 | §7.2 第 4 點改引本報告 repo 路徑（1112 行），不再引用暫存檔 |
| C-21 | 已修正 | (a) AT-966-3-2 Given 與預期已涵蓋 `lastSkip`、`runs.waiting`、`push.retry`、`tickAt`（423 行）；(b) `schedule:null` 於 AT-966-5-9 與 12-7 同句「…沒有排程資訊」；(c) `push.retry` 列入 W-F14 不採用清單（106 行）；(d) FRD 摘要補「為什麼沒有啟動運轉」（62 行）；(e) 前端夾具 camelCase 與 `camelKeys` 輔助已寫入（143、1040 行）；(f) 黃金 `detail` 為整個 `items[0]`、`FAKE_CLI` 整個輸出（390 行） |

## T2. `filter_detail` 白名單與根層 TCS-P7 §2.1 的鍵集合比對

逐塊比對 Console C-3（白名單的唯一依據，W-F4 明定「契約 C-3 列出的鍵」）與根層 §2.1：`detail` 頂層八欄（`patch、body、sourceObs、heldout、sandbox、verify、next、timeline`）、`patch`／`body` 四鍵、`sourceObs[]` 五鍵加缺列的 `{id,missing}`、`heldout` 八鍵、`sandbox` 七鍵、`verify` 九鍵加 `reasons[]` 兩鍵、`next` 三鍵、`timeline[]` 五鍵——**完全相同，無多無少**；`ne[]` 與 `items[0]` 其他鍵不在白名單作用範圍（只作用於 `items[0].detail`），根層新碼項的 `ne.text` 不受影響。計數：AT 定義 113（非 E 91、E 22）；§3 分類 20＋10＋75＋8＝113；各 AC 分項加總 113；RTM（1＋1＋17＋113＝132 列）、Implementation_Plan、TCS 第 45 行一致。

## T3. 新發現

| 編號 | 嚴重度 | 位置 | 問題 | 建議修法 | target |
|---|---|---|---|---|---|
| C-22 | P3 | TCS 第 37 行 FRD After(6)；PRD §0.12-6（228 行） | 引入 `filter_detail` 後仍有兩處舊敘述與 W-F4 矛盾：TCS FRD After(6) 寫「backend 與 Bridge 原樣透傳、Bridge 與 backend 程式零邏輯改動」；PRD §0.12-6 寫「經 Bridge、backend 原樣透傳」。實作者讀到會以為 Bridge 不得加白名單，或把它當成越權 | TCS 改為「backend 原樣透傳、Bridge 只加純函式 `filter_detail`（只放行契約鍵）」；PRD 同改一句 | console |
| C-23 | P4 | W-F4、AT-966-4-6、AT-966-1-8、§7.3 | (a) 白名單依據「C-3 的鍵」而 `sourceObs` 缺列形態 `{id,missing:true}` 只是括號帶過，AT-966-4-6 的突變清單也沒列 `missing`（黃金樣本列含 `missing:true`，有間接覆蓋，但建議顯式）；(b) 白名單意味著根層日後新增 `detail` 欄位時 Bridge 會靜默丟棄，需走 Console 勘誤才看得到，§7.3 未寫成已知邊界；(c) AT-966-1-8 的唯讀鎖普查只提 `si_report.py`，未納入新模組 `app/si_detail.py` | 各補一句：C-3 把 `missing` 列為 `sourceObs` 的正式鍵並加進突變清單；§7.3 加一條「根層新增 detail 欄位必須同步改白名單與 C-3」；AT-966-1-8 的普查範圍加 `si_detail.py` | console |

## T4. 三審結論

**CONDITIONAL**。二審的 C-17～C-21 已全數修正，白名單與根層契約鍵集合完全一致，數量三處一致。無 P1、無 P2；剩 C-22（P3，兩句舊敘述）與 C-23（P4）。依門檻不阻擋凍結，建議凍結前順手改這兩處（否則凍結後只能走勘誤）。refreeze 清單不變（PRD 8 把、Architecture 僅 `agentconsole-si-schedule`）；唯本輪又改動 PRD／Architecture／TCS，凍結時以各鍵 `show --json` 摘要現查為準。

---

# 終審（2026-11-11；範圍僅限三審 C-22、C-23；讀現行檔案自行驗證）

結論：**PASS**（無未結發現）。

| 編號 | 結果 | 證據 |
|---|---|---|
| C-22 | 已修正 | TCS 第 37 行 FRD After(6) 改為「Bridge 只放行契約列出的鍵、其餘丟棄（新純函式 `filter_detail`，W-F4），backend 只做鍵名轉換」；PRD §0.12-6（228 行）同步改寫；對 TCS、PRD、Architecture 搜尋「原樣透傳／零邏輯」，剩下的命中只有 TCS 第 54 行（「backend 原樣透傳、Bridge 只放行契約列出的鍵」）與 Architecture 第 548、1179 行（皆明指 backend），無任何與白名單矛盾的句子 |
| C-23 | 已修正 | (a) C-3（145 行）新增 `sourceObs` 缺列形態 `{id,missing:true}` 的正式契約句並把 `missing` 列入白名單鍵，AT-966-4-6（403 行）突變清單加入「漏列 `missing` 鍵（`{id,missing:true}` 被削成 `{id}`）亦紅」；(b) §7.3（1115 行）補「根層新增 `detail` 欄位時須同步改白名單」；(c) AT-966-1-8（336～337 行）普查納入 `app/si_detail.py` 並以「開檔或呼叫子行程即紅」鎖住其純函式性質 |

新矛盾檢查：AT 定義仍為 113（非 E 91、E 22），與 §3、RTM 132 列、Implementation_Plan 的先前核對值無變動；白名單鍵集合與根層 TCS-P7 §2.1 仍相同（`missing` 為根層 `sourceObs` 缺列形態的既有鍵，與 §2.1 一致）。

最終結論：**PASS**。三輪審查發現（一審 P2×7、P3 多筆、二審 C-17～C-21、三審 C-22／C-23）均已修正並驗證；refreeze 清單維持第 4 節（PRD 8 把、Architecture 僅 `agentconsole-si-schedule`），凍結時以各鍵 `show --json` 摘要現查為準。
