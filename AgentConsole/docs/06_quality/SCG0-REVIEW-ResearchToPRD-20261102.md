# SCG-0 獨立審查報告：ResearchToPRD W0 規格波（QA；唯讀、零信任）

> 審查日期 2026-11-02；審查者＝QA（Sonnet 5.5）；體例照 `SCG4-REVIEW-ExecMonitorEntry-20261101.md`（A～G）。A～G 為**一審定稿**（九個維度皆已完成，抽樣深度見 G）；**H 節為二審、I 節為三審**（B.1 為三審判定，B.2 保留二審、B.3 保留一審判定）。落檔路徑（主控）：`AgentConsole/docs/06_quality/SCG0-REVIEW-ResearchToPRD-20261102.md`。不含任何檔案雜湊值。

## A. 審查範圍與輸入快照

QA 工作目錄 S＝scratchpad 的 `r2p` 子目錄；R＝本 repo 工作樹（HEAD `01d9be6e`＋未 commit 的 M／??）。輸入一律只讀；所有自寫腳本在 `S\qa\`，以 `python -I` 執行，可重跑。

| 對象 | 檔（相對 S 或 R） | 讀到的版本號／首行 |
|---|---|---|
| 主控裁決 | `S\HELM_DECISIONS.md` | D-12～D-59（D-01～D-11 為 PRD 附錄 C.1 的預決；PRD 附錄 C 登記 D-01～D-59；我重數：HELM 內 D-12～D-59 共 48 列、無缺號） |
| Console 側（SD-A） | `sd\docs\01_requirements\ResearchToPRD_PRD.md`（1715 行）、`sd\AgentConsole\docs\02_architecture\{ADR-003-ResearchToPRD.md, API_Contract_ResearchToPRD.md, Architecture_delta.md}`、`sd\docs\04_planning\ADR\ADR-XPLAT-017-bridge-fsm-write-surface.md`、`sd\docs\01_requirements\Agent_ConsoleUI_PRD_delta.md`、`sd\AgentConsole\docs\04_planning\ResearchToPRD_Plan.md`、`sd\_aux\ID_INDEX.md` | 七檔首行皆「輸入快照：HEAD＝01d9be6e；主控裁決 D-01～D-59」；PRD 檔頭「v1.0.0-rc2」 |
| 框架側（SD-B） | `sdf\AISDLC_SDD\AISDLC_SDD_v0.30\` 下九個新檔、`sdf\FRAMEWORK_EDITS.md`（E01～E36；48 塊／13 檔）、`sdf\FRAMEWORK_VERIFY.md`、`sdf\apply_framework_edits.py`、`sdf\r2p_contract_check.py` | 檔頭「輸入快照：HEAD＝`01d9be6e`；LATEST＝`AISDLC_SDD_v0.30`」 |
| P0 測試契約（SD-C） | `sdc\AgentConsole\docs\03_testing\contracts\TCS-ResearchToPRD-P0-20261102.md`（1917 行）、`sdc\AgentConsole\docs\06_quality\RTM-ResearchToPRD-P0-20261102.md`（237 行）、`sdc\_aux\{RTM_stub_2_10.md, SELF_CHECK.md, selfcheck.py}` | F-906／US-920～922／AC-960-1～24／AT 200 |
| 主控預先落檔 | `.gitignore`、`.github/workflows/agentconsole-ci.yml`、`AgentConsole/.env.example`、`AgentConsole/docker-compose.yml`、`docs/04_planning/ADR/ADR-XPLAT-016-…`、`AgentConsole/CLAUDE.md`、`AISDLC_SDD/scripts/framework_status_snapshot.py`（均為 R 內未 commit 的 M；另 `docs/01_requirements/ResearchSOPtoPRD_Source_Spec.md` 為 ??） | 全部 LF、無 BOM；`AgentConsole/CLAUDE.md` 167 行（不超過 200） |
| 上位真相源 | 來源規格（316 行）、`transition_rules.py`、`fsm_runtime.py`、`state_loader.py`、`SDD_AUTOCLAUDE_BRIDGE.md` §8、`SDD_SPEC_FIRST_GATE.md`、`AISDLC_SDD/CLAUDE.md` Rule 5、`FILE_DIRECTORY_RULES.md`、`registry.ts`、`SecurityConfig.java`、`sdd_cli.py`、`security.py`、`test_sdd_cli.py`、`V6__audit_log.sql`、`AuditLoggingFilter.java`、`AuditPersistenceApiIT.java` 等 | 唯讀現查 |

## B. 判定與計數

### B.1 三審結果（最新；逐條核對與新發現見 I）

**判定：PASS**。P1＝0、P2＝0、P3＝1（F-25）、P4＝0。二審的 F-21～F-24 依 D-65 全數落實（落實 4、部分落實 0、未落實 0），SD-C 順手對齊四處、SD-A 三句敘述與 D-65 範圍字樣一致性皆落實；F-21 的排除條件我在拋棄式庫以測試原 SQL 實測，P0 庫前後快照逐值相等，F-22 的 floor 探針 0、49、101 被擋、50、100 通過。三審新發現的 F-25（解析不出 host 的被拒外呼無法入庫，與 AT-960-8-1 的 `file://` 形態）為 P3，建議凍結前補一句話，不擋凍結。至此一審、二審共 24 項發現全部關閉。

### B.2 二審結果（保留紀錄；細節見 H）

**判定：FAIL**。P1＝0、P2＝1（F-21）、P3＝0、P4＝3（F-22、F-23、F-24）。一審 20 項發現：落實 18、部分落實 2（F-01、F-09）、未落實 0。一審 P2 四項中，F-02、F-11、F-12 逐字驗證落實；F-01 部分落實——一審六項硬釘與 SD-C 重掃新增的 #24～#28 皆在位，但我以獨立掃描另找到一項仍未收的硬釘（`BackupJobMigrationIT` 的前後快照相等斷言，記為 F-21），同類問題、同樣是「凍結後既有測試必紅、而 PKG-DB 無權改」，所以仍擋凍結。修法只需 SD-C 補一列（§4、§5.7、RTM；SD-A 另在計畫書 L4 消費端補一句）；F-22～F-24 為 P4 建議，不擋凍結。

### B.3 一審結果（保留紀錄）

**判定：FAIL**（SCG-0 不放行；P2 四項修畢並經複審後再議）。

| 嚴重度 | 計數 | 發現 |
|---|---|---|
| P1（阻斷凍結） | 0 | — |
| P2（凍結前必修） | 4 | F-01、F-02、F-11、F-12 |
| P3（實作期可修） | 10 | F-03、F-04、F-05、F-06、F-07、F-08、F-09、F-10、F-13、F-14 |
| P4（建議） | 6 | F-15、F-16、F-17、F-18、F-19、F-20 |

**P2 一句話清單（該棒）**

1. F-01（SD-C）：TCS §4／§5.7 的「需同步既有測試」清單漏列 6 個會因本期變紅的既有測試（四個 Flyway 版本清單 IT、`OpenApiIT:247`、`si.endpoints.test.ts:44-47`），且 §4 #10 與既有 AT_950_9_E_1 直接互斥。
2. F-02（主控先裁決；SD-A 主修、SD-C、SD-B 同步）：ESCALATION 人工恢復後的審查預算語意在三側文件與 AT 全無，且與 FSM 真實行為（恢復不歸零）不同。
3. F-11（主控改 D-52 措辭；SD-A、SD-C）：「`audit_log` 列標 `note=research.allowlist`」與「403／422 不增列」兩宣稱都與既有 `V6__audit_log.sql`、`AuditLoggingFilter`、`AuditPersistenceApiIT` 互斥，AT-960-5-4 在真實後端必紅。
4. F-12（SD-A）：PRD 附錄 C.7 的 D-48 仍是主控已更正前的「三份上位文件（INIT、SPEC_FIRST_GATE、BRIDGE）」。

**為何都不是 P1**：四項的修法都是文字／AT 改寫，不動設計、DDL、安全邊界，也不涉及 Rule 9 絕對禁令或非法 FSM 邊；F-01 與 F-11 最接近 P1（凍結後會有 AT 在真實環境必紅、開發棒依規不得動既有測試），若主控認定「凍結後不得靠勘誤補救」可升 P1，**結論（FAIL）不變**。
**維度結論**：維度 1（完整性）、5（FSM 合法性）、8（docs 閘）、9（框架側）除上列外無 P1／P2；維度 4（憲法與鐵律）與 6（安全）在抽樣範圍內無 P1／P2（F-07 為安全相鄰的 P3）。

## C. 發現表

> 格式：F-NN｜維度｜嚴重度｜`檔:行`｜逐字證據｜為何是問題｜修法｜該棒。「裁決層」＝問題出在主控裁決的措辭本身。

### F-01｜維度 7／3｜**P2**｜TCS §4 同步清單與 §5.7 允許變更集合漏列「會因本期而變紅的既有測試」（共 6 檔）

證據（我逐檔現查 R）：
1. 四個 Flyway 版本清單 IT 都在 `flyway(database, null).migrate()`（最新版）之後硬釘 `containsExactly("1",…,"15")`：`AgentConsole/backend/src/test/java/com/aisdlc/console/infrastructure/persistence/V5UpgradeMigrationIT.java:135`、`IssuePriorityMigrationIT.java:131`、`BackupJobMigrationIT.java:168`（方法名 `AT_BK_10_1_2_theMigrationHistoryIsExactlyOneToFifteen…`）、`SiConsoleWritesMigrationIT.java:129`。TCS §4 #13 只列 `SchemaMigrationIT.java:63-68`（`TCS:1739`）；§5.7 PKG-DB 的允許集合只含 `SchemaMigrationIT.java（只改版本清單）`（`TCS:1830`）。V16～V18 落地後這四檔必紅，而 PKG-DB 無權改。
2. `OpenApiIT.java:247`：`assertThat(docs.<Map<String, Object>>read("$.paths").keySet()).as("本鍵不新增路徑").hasSize(77);` ——另一個硬釘 77 路徑的斷言。§4 #14 只列 `:43`、`:145`、`:153`、`:169`、`:399` 起（`TCS:1740`）；P0 加 24 條路徑後 `:247` 必紅。
3. `AgentConsole/frontend/lib/api/si.endpoints.test.ts:44-47`（AT_950_9_E_1 第二個 it）：`const source = readFileSync(path.join(ROOT, "lib", "api", "endpoints.test.ts"), "utf-8"); expect(source, "總數釘選必須是 84").toContain("expect(names).toHaveLength(84);");`。TCS §4 #10 卻要求把 `endpoints.test.ts:204` 的 `toHaveLength(84)` 改成 109（`TCS:1731`）——照做即令這個**原始碼字串釘選**變紅；該檔不在 §4、不在 PKG-FE-A 允許集合（`TCS:1835`），且 AT_950_9_E_1 住在凍結的 SI 測試契約，§4.4 也沒有對應勘誤。**§4 #10 與既有 AT 直接互斥。**

為何是問題：TCS 自稱「需同步的既有測試（只改預期值，不刪斷言）」是開發棒的唯一許可清單（§5.7＋AT-960-18-5 的 GATE 核對）；漏列＝凍結後 PKG-DB／PKG-FE-A 一跑全套就紅、而依規定不准動，只能回報主控走勘誤——正是「凍結後會出事」。
修法：SD-C 把上列補進 §4（#13 子項四檔；#14 加 `:247`；#10 加 `si.endpoints.test.ts:46` 的 `toContain` 字串同步為 109 並在 §4.4 增列對應凍結 TCS 勘誤）、§5.7（PKG-DB 加四個 IT、PKG-FE-A 加 `si.endpoints.test.ts`）與 RTM 對應列；並由主控請 SD-C 對 `AgentConsole/backend/src/test`、`frontend/lib`、`engine-bridge/tests` 重跑一次「硬釘計數」掃描（我只掃了 Flyway 版本清單、`hasSize(77|89)`、`toHaveLength(84)` 三族，不保證窮盡）。
該棒：**SD-C**。

### F-02｜維度 5／1｜**P2**｜ESCALATION 人工恢復後的審查預算語意在三側文件與 AT 全無，且與 FSM 真實行為不同

證據：
- FSM：`fsm_runtime.py:1194-1218`（`resume_from_escalation`：只轉 `ESCALATION→RESUME_VERIFICATION→<to>`、回填 `escalation_history`，**不動 retry 計數**）；`reset_retry` 只在 `gate PASS`（`fsm_runtime.py:536`）與 `record_spec_frozen`（`state_loader.py:305-308`）。`state_loader.py:237-248`：`increment_retry` 見 `prior >= limit` 時標「(tamper detected: prior_count=… ≥ limit=…)」並 `current = limit`。⇒ 3 次 FAIL→ESCALATION→人工 `resume-from-escalation --to SPEC_DRAFTING` 後，`SCG_VALIDATION.current_count` 仍為 3；下一次 `gate SCG_VALIDATION FAIL` 立即再 ESCALATION（歷史列還帶「tamper detected」字樣），只有 `gate PASS` 能歸零。
- 文件：WF §2.5「預算耗盡後仍要繼續的合法做法：人恢復後繼續修訂」（`SDD_RESEARCH_TO_PRD.md:169`）、API-RP-11「`iterate`＝`revise`→`review` 重複至通過或耗盡（上限由 FSM `SCG_VALIDATION`＝3 次 FAIL…）」與「`[一鍵自動迭代修正]` … 顯示剩餘預算＝`3 − fsmRetryCount`」（`API:227,314`）、PRD FR-R2P-09「剩餘預算＝3 − FSM 已 FAIL 次數」（`PRD:586`）、AC-R2P-18-6／AT-960-15-4～5（「我已恢復，繼續」只驗現態離開 ESCALATION 後 202 續跑）——都沒說「恢復後預算不歸零：每次恢復至多再得一次審查、再 FAIL 立即再 ESCALATION」。

為何是問題：UI 會在恢復後顯示 ≤0 的「剩餘預算」、`iterate` 會在第一次 FAIL 就停；開發棒若依 AT-960-12-E-2 的 `fake_sdd`（「遵守 retry 規則」，未定義恢復後行為，`TCS:1069`）實作，會與真 CLI 行為分歧；R-9.1「有界停機」的語意（每次人工恢復的預算）屬需裁決的設計點，不能留給實作期猜。
修法：由主控裁定恢復後預算語意（建議：不歸零、每次恢復＝一次審查機會；要全新預算＝換世代鍵 `research-<slug>-g2`，WF §2.5 已有此路），然後（a）SD-A：PRD AC-R2P-08-3／18-6 與 FR-R2P-09 的剩餘預算算式（`max(0, 3 − currentCount)`）、ADR-XPLAT-017 D6 補一段「恢復後」列、API-RP-11 `iterate` 說明；（b）SD-C：AT-960-15-5 或新 AT 以暫存狀態目錄實跑「3 次 FAIL→人工恢復→下一次 FAIL 立即再 ESCALATION、PASS 歸零」並讓 `fake_sdd` 對齊真行為；（c）SD-B：WF §2.5 與審查卡模板 §2.3 各補一句。
該棒：**SD-A 主修、SD-C、SD-B 同步**（主控先裁決）。

### F-03｜維度 2／7｜P3｜`docker-compose.yml` 座標被主控預先落檔位移 3 行

證據：`PRD:961`（NFR-R2P-11 `docker-compose.yml:227、254–284`）、`PRD:1178`（§9.0 的 Q 表第 4 列「`BRIDGE_ALLOWED_PATH_ROOTS: /workspace`（`docker-compose.yml:227`）」）、`ADR003:100`（同 `:227`）。現行工作樹：`AgentConsole/docker-compose.yml:227` 是 `BRIDGE_DB_DSN:`，`BRIDGE_ALLOWED_PATH_ROOTS: /workspace` 在 `:230`；唯讀 bind 長語法區自 `:260` 起（原 `254–284` 在 backend 區塊加三行權杖註解後整體 +3）。座標是 HEAD 值、預先落檔使其過期。
修法：落檔時主控 `Edit` 三處座標為 `:230` 與 `:257–287`（或改成符號名）。該棒：主控收尾（SD-A 文字）。

### F-04｜維度 2／3｜P3｜預檢代碼詞彙 `CITES_V1`／`CITES_UNANCHORED` 沒有單一真相源

證據：PRD AC-R2P-05-2 只寫「預檢報 `CITES_V1`」（`PRD:502`）；TCS AT-960-9-3 另斷言 `CITES_UNANCHORED`（E-003）與「預檢 P0-7」（`TCS:933,936`），RTM:117 同；框架模板 P0-7 只有條件文字、沒有代碼名（`PRD-SPEC-ENGINEERED-TEMPLATE.md:42`）。代碼名只存在於 TCS 的斷言。
修法：SD-A 在 AC-R2P-05-2／07-3 或 §5.1.3 登記預檢代碼表（`CITES_MISSING`、`CITES_V1`、`CITES_UNANCHORED`、`CITES_CANDIDATE`），SD-B 在模板 P0-7 欄補代碼；SD-C 對齊。該棒：SD-A（主）、SD-B。

### F-05｜維度 4／6／3｜P3｜「研究抓取清單＝同一檢查函式 `check_outbound_url` 的獨立實例」與 TCS 的嚴格判準不符

證據：`security.py:275-303`：`check_outbound_url` 接受 `http` 與 `https`（`parts.scheme not in ("http","https")`）、接受任意埠（只驗可解析）、並 `rstrip(".")` 把尾點視為相同 host。NFR-R2P-03-1「僅 HTTPS」（`PRD:901`）、D-35「同一檢查函式」、ADR-003 D7、TCS AT-960-8-1 要求 `http://`、`:8443`、尾點 host 一律 `DENIED_ALLOWLIST`（`TCS:866`「埠與尾點不做正規化放行」）。「同一檢查函式」若照字面不加判準會放行三者；若改既有函式則動到既有 `test_security`（模型端點清單語意）。
修法：SD-A 把 D-35／ADR-003 D7／NFR-R2P-03-1 改述為「`check_research_url`＝先呼叫 `check_outbound_url` 取 parser 一致性判準，再加 https 限定、埠 443 限定、尾點拒絕與私網 IP 判準；不修改 `check_outbound_url`」。該棒：SD-A；SD-C 無需改 AT。

### F-06｜維度 2／9｜P3｜PRD／ADR／計畫書仍寫「DDL 斷言住 `SchemaMigrationIT`」，TCS ⚖9 改放新類別 `ResearchSchemaMigrationIT`

證據：`PRD:1212`（C13）、`PRD:1266`（機械鎖⑦）、`ADR017:127`、`ARCH:845`、`PLAN:43,176` 皆寫 `SchemaMigrationIT`；TCS `:60,1830,1879`（⚖9）明文放新類別且說明（「既有 SchemaMigrationIT 只改版本清單」）。⚖9 已記錄偏離與 WHY，故僅屬名稱漂移。修法：SD-A 把五處改為 `ResearchSchemaMigrationIT`（版本清單仍屬 `SchemaMigrationIT`）。該棒：SD-A。

### F-07｜維度 2／5｜P3｜FR-R2P-19 標題「（資料表隨 P0）」與 V19 為 P1 矛盾

證據：`PRD:782` 標題「〔P1 後端與 FSM 序列證據／P2 看板發起鈕與橫幅（資料表隨 P0）｜新建〕」；`PRD:146`「V19（分流、SCR、拆解、交付表與自癒視圖）於 P1 一次建立」；`Architecture_delta.md:719,767`（`research_scr` 在 V19＝P1）。三處對「SCR 表何期建立」說法不一。修法：SD-A 改標題為「（資料表隨 V19〔P1〕）」。該棒：SD-A。

### F-08｜維度 5｜P3｜SCR MINOR 序列的內環現態前置條件未列，且「先發佈、後 `transition →SPEC_AUDIT`」的順序與框架的 SPEC_AUDIT 狀態紀律／人工等價序列不一致

證據：ADR-XPLAT-017 附錄 A 步驟 2「發佈新 PRD 到目標 docs/（複製＋…），然後內環鍵 I：`transition --to SPEC_AUDIT`…」（`ADR017:146-151`）；`transition_rules.py:46,59,66`：只有 IMPLEMENTATION／EXECUTION_EVALUATION／ADVERSARIAL_EVALUATION／PR_REVIEW 有 `→SPEC_AUDIT` 邊，RTM_VERIFY（`:68`）與 RELEASE_READY（`:77`）沒有；`AC-R2P-19-1`「內環鍵回 IMPLEMENTATION」未說明從哪些現態、經哪條邊。`SDD_AUTOCLAUDE_BRIDGE.md:467-470`（§8.3 第 3 點）：非草擬態時 hooks-ON 視窗擋 `docs/01～03` 的 Write／Edit；ADR-017 附錄 A 末句稱「人工等價：同一序列在 hooks-ON 的 SDD session 手跑」——先發佈（寫 `docs/01_requirements`）在 IMPLEMENTATION 態會被擋，等價序列走不通。
修法：SD-A 在 ADR-017 附錄 A／AC-R2P-19-8 補「現態矩陣」（RTM_VERIFY／RELEASE_READY 須先 `gate … FAIL` 回 IMPLEMENTATION 或回報 BLOCKED）並把順序改為 `transition →SPEC_AUDIT`→發佈→`spec-refreeze`→`transition →PR_REVIEW`→`gate PR_REVIEW FAIL`；屬 P1 期，P0 凍結可帶；該棒：SD-A。

### F-09｜維度 3／8｜P3｜DDL 結構一致性未釘（V16～V19 尚未發佈，現在補不留後遺症）

在拋棄式資料庫（本機 `autoclaude_pg` 容器內臨時建庫 `qa_scg0_ddl`，用畢已丟；repo 零寫入）以 V1～V15＋Δ14 抽出的 V16～V19 全數 `psql` 套用 rc 0；跑 66 個行為探針（腳本 `S\qa\ddl_tests.sql`、`ddl_tests2.sql`）：D-42／D-50／D-55／D-57／D-59 的 CHECK 與觸發器全部如設計（見 D 節）。僅下列被接受（探針 `R01／R06／R14／R15／R17`）：
- `passed=false` 卻 `verdict='PASS'`（V18 輪表 CHECK 只單向約束 `passed ⇒ verdict='PASS'`）；
- `verdict='ESCALATE'` 但 `escalated=false`、`fsm_retry_count` 為 NULL 或與 `fsm_gate_result` 不對應；`escalated=true` 卻 `verdict='REVISE'`；
- `threshold`／`floor_score` 無範圍 CHECK（params 快照可被寫成 0 後使 `passed` CHECK 恆真）。

AC-R2P-08-7／08-11 的字面都被滿足，所以不是違反規格；但 D-58(a) 的目標是「型別層把列存在＝已完成且與 gate 一一對應鎖死」。修法（建議）：加 `CHECK ((verdict = 'PASS') = (passed IS TRUE))`、`CHECK (escalated = (verdict = 'ESCALATE'))`、`CHECK ((fsm_retry_count IS NULL) = (fsm_gate_result IS NULL))`、`CHECK (threshold = 85.00 AND floor_score = 60)` 或至少 `BETWEEN`；對應補 AT-960-1-E-7 的負控。屬 P3（實作期可修，但改 DDL 要在 V16～V18 發佈前）；該棒：SD-A（Δ14）＋SD-C（AT）。

### F-10｜維度 8／2｜P3｜來源規格逐字檔不在任何落檔清單，也不在 D-46 的根層例外清單

證據：`docs/01_requirements/ResearchSOPtoPRD_Source_Spec.md` 現為 `??`（R 的 `git status`：未追蹤）。PRD:10、:1438、:1456、:1467 與 `Agent_ConsoleUI_PRD_delta.md:17` 都以它為「逐字存檔」並回指章節；但 `ResearchToPRD_Plan.md:28-40`（W0 表）與 PRD §9.0 落點表都沒列它；AT-970-5-1 的 `$rootExempt` 只有 6 檔＋`AgentConsole/`（`TCS-Framework:563-570`），ADR-XPLAT-017 §D7 機械核對法（`ADR017:103`）同。
為何：若落檔 commit 漏 `git add` 它，PRD 五處路徑宣稱在他機 clone 後是幽靈（`TestR81GhostPathClaims` 的掃描面 `_PATH_CLAIM_GLOBS`＝`test_doc_loc_baseline_freshness_r60.py:3948-3958` 只含根 `CLAUDE.md`、`ONBOARDING.md`、兩份 `CrossPlatform_*` 準則、`*HANDOFF*.md`、`docs/04_planning/ADR/*.md`、`AutoSDD_improving_*.md`，不含 `docs/01_requirements/`，機械閘看不到）；若在 `$base`（Stage-1 採納當下的 HEAD）之後才補 commit，AT-970-5-1 的「追蹤檔變更掃整個 repo」會因該路徑不在 `$allowed`／`$rootExempt` 而紅。Plan §8 的順序（落檔→QA→開鍵）使後者不會發生，所以只列 P3。
修法：SD-A 在 Plan §2 W0 表與 PRD §9.0 落點表補一列「來源規格逐字檔（主控已預先落檔，W0 同 commit 收入）」；主控落檔 commit 一併 `git add` 該檔；不必改 `$rootExempt`（在 `$base` 之前入庫）。該棒：SD-A（文字）＋主控（落檔）。

### F-11｜維度 7／3／2｜**P2（裁決層＋文件＋AT）**｜「`audit_log` 列標 `note=research.allowlist`」與「403／422 不增列」兩宣稱都與既有程式碼和既有 IT 互斥

證據：
- 宣稱：D-52（`HELM_DECISIONS.md:52`）「console-api 以既有 `AuditTrail` 寫 `audit_log`（`note` 標 `research.allowlist`）」；`PRD:474`、`PRD:484`（AC-R2P-04-7：「為該請求的 `audit_log` 列標 `note=research.allowlist`」）、`PRD:1674`、`ARCH:223`、`API:247`（`AuditTrail.note("research.allowlist", "research_allowlist", <條目 id>)` 為該請求的 V6 `audit_log` 列留痕）、`TCS:1364`（AT-960-5-4：「各使 `audit_log` 多恰一列…`note` 含 `research.allowlist`…Reddit 未確認 422 `terms_ack_required` 且不增列…OPERATOR 與 VIEWER 回 403 且 `audit_log` 不增列」）、`TCS:1894`（⚖ 列同）。
- 現況（欄位）：`V6__audit_log.sql:6-17` 欄位只有 `id, occurred_at, subject, role, method, path, entity_type, entity_id, http_status, trace_id`——沒有 `note`／`action` 欄。`AuditLogWriter.java:29-30`：`Entry(subject, role, method, path, entityType, entityId, httpStatus, traceId)`，無 action。`AuditLoggingFilter.java:82-85` 只把 `action`／`entity` 放進 `audit` logger 的 JSON 日誌行，`:91-92` 落庫時不帶；`AuditTrail.note(...)` 的標註只影響 `entity_type`／`entity_id` 兩欄（`RequestAuditTrail.java:50-53`）。
- 現況（不增列）：`AuditLoggingFilter.java:32-34`「放在 JWT 與限流 filter 之後、授權之前，因此被拒絕的寫入（401／403／429）同樣會留下審計紀錄」；`:63-93` 在 `finally` 內無條件 `writer.write(...)`（含 `response.getStatus()`）；既有 IT `AuditPersistenceApiIT.java:76-88`（`rejectedWritesAreRecordedWithWhoTriedAndAnonymousOnesWithNullSubject`）釘住「VIEWER 刪除回 403 → 一列 `http_status`＝403、`role`＝VIEWER；匿名回 401 → 一列 `subject`＝null」。

為何是問題：(1) AC-R2P-04-7 與 AT-960-5-4 要求斷言一個不存在的欄位；(2) AT 對 OPERATOR／VIEWER 的 403 與 Reddit 未確認的 422 斷言「`audit_log` 不增列」，在真實後端必紅（每個 `/api/` 寫入請求恆一列，與有無 `note` 無關）；(3) D-52 措辭本身在裁決層即不可照字面實作。開發棒依凍結 TCS 無法同時讓 AT 綠與不動 V6／Filter（既有 `AuditPersistenceApiIT` 不得紅）。
修法：主控把 D-52 改成「ADMIN 的 allowlist 新增／停用，由 console-api 以 `AuditTrail.note("research.allowlist", "research_allowlist", <條目 id>)` 標註：既有 `audit` 日誌行帶 `action=research.allowlist`、`entity=research_allowlist:<id>`；V6 `audit_log` 列（每個寫入請求本就一列）的 `entity_type='research_allowlist'`、`entity_id=<條目 id>`；不新增欄位、不改 V6」（若要求資料庫內可依動作過濾，唯一的結構正解是另開 Flyway 加 `action` 欄，屬 V16 範圍擴充、須主控另裁，不建議）。SD-A：`PRD:474／484／1674`、`ARCH:223`、`API:247` 依之改寫；SD-C：AT-960-5-4 改為「ADMIN 新增（201）／停用（200）各使 `audit_log` 多恰一列，`entity_type='research_allowlist'`、`entity_id`＝條目 id、subject＝JWT subject、role＝ADMIN；Reddit 未確認 422 亦多一列（`http_status` 為 422）；OPERATOR／VIEWER 的 403 亦各多一列（`http_status` 為 403、迷你 Bridge 請求數 0）；全程 `research_events` 列數不變」，`action` 字串改以 `audit` logger 的日誌擷取斷言（或不斷言），`TCS:1894` 的 ⚖ 列同步。
該棒：**主控（D-52 裁決措辭）＋SD-A＋SD-C**。

### F-12｜維度 2／1｜**P2**｜PRD 附錄 C.7 的 D-48 仍是「三份上位文件（INIT、SPEC_FIRST_GATE、BRIDGE）」——主控已更正的前一版

證據：`ResearchToPRD_PRD.md:1670`「(1) 框架鍵適用增量（delta）條款：三份上位文件（INIT、SPEC_FIRST_GATE、BRIDGE）的改動＝只增不減的註冊與條文增補，收尾 `spec-refreeze`」；`HELM_DECISIONS.md:48` 現行 D-48(1)「Stage-1 採納的三份上位文件（BRIDGE §8.4 `sdd` 列＝`AISDLC_SDD/CLAUDE.md`、`AISDLC_SDD_INIT.md`、`SDD_SPEC_FIRST_GATE.md`；SD-B 修訂交卷指正，原寫 BRIDGE 有誤）的改動＝只增不減的註冊與條文增補，收尾對這三份 `spec-refreeze`；BRIDGE 不在凍結集合、同樣只增不減」。框架側已對（`TCS-Framework:32`、`:1147`、`:1153`；`FRAMEWORK_VERIFY.md:243` 是 SD-B 當初指出差異的原話，屬歷史說明、不是缺陷）。我以 `S\qa\scan_dtext.py` 逐列比對 PRD 附錄 C 與 HELM：裁決欄不同 3 列（D-42、D-48、D-53）、WHY 欄不同 2 列（D-13、D-59），D-40 在 PRD 以 C.6 呈現；只有 D-48 是語意差異（其餘見 F-14）。
為何：PRD 附錄 C 是主控裁決的登記處（`PRD:10`「主控裁決 D-12～D-59…WHY 逐條記載」）；D-48 決定收尾 `spec-refreeze --doc` 的檔集合（`TCS-Framework:1147`）。PRD 是 SD-C 與開發棒的上位文件，留著舊句＝讀者會以 BRIDGE 為凍結集合成員；任務書規定「文件違反裁決＝P2 以上」。
修法：SD-A 以 HELM 現行 D-48 全文覆蓋 `PRD:1670` 的「裁決」欄（含「BRIDGE 不在凍結集合」一句），並順手同步 F-14 的其餘四列。
該棒：**SD-A**。

### F-13｜維度 3／2｜P3｜（任務書已知待辦，時序造成）SD-C 的 AT-960-4-7 與 AT-960-16-E-3 對 SD-A 最後才定的 DTO 字面未對齊；另 16-E-3 的「Gate 0 決定表」替身沒有對應端點

證據：
- SD-A 最終契約：`API:162` `ReviewRoundDto` 含 `fsmGeneration: number`；`API:172-176` `ResearchFsmViewDto extends SddFsmState`，`retryHistory: SddRetryHistory & { gates: Record<…, { currentCount; entries }> }` 與 `humanReturnCount`（「目前 fsm_generation 內 `research_gate_decisions` 中 gate=GATE0、decision=CHANGES 的筆數」）。
- AT-960-4-7（座標見本條末行）：Then 沒有 `fsmGeneration`，OpenAPI `required` 只斷言 `startedAt`、`finishedAt`、`passed`、`verdict`——**不矛盾，是缺口**（欄位存在、但無 AT 守它必填）。
- `TCS:1509-1512`（AT-960-16-E-3）：Given 三支 fetch 替身＝審查輪表、**Gate 0 決定表**（`decision` 為 CHANGES 者為人工退回）、`GET …/fsm` 的 `retryHistory.count`；對照式「`retryHistory.count` ＝ 目前 `fsm_generation` 中 `fsmGateResult` 為 FAIL 的輪數 ＋ 人工退回筆數」。我把六組（甲～己）逐組代入該式：甲 2＝2＋0、乙 2＝1＋1、丙與丁因 `count` 為 1 與 3 而警示、戊 1＝0＋1、己 1＝1＋0——**與契約語意一致**；`retryHistory.count`（既有 `routers/sdd.py` 的 `_retry_history` 對各閘 history 筆數加總；外環鍵只有 SCG_VALIDATION 有史）在數值上等於 `gates.SCG_VALIDATION.entries`。
- 缺口：(a) 契約已把「人工退回筆數」放進同一個 `GET …/fsm` 回應的 `humanReturnCount`，而 P0 的 25 個 operationId（`TCS:1369`、`API` §1.1）沒有任何回傳「決定表」的端點（最近的 `getResearchRecordsAudit`＝`API:80` 是 FR-02／AC-02-4 的紀錄稽核）⇒ AT 的第三支 fetch 替身在真實 API 沒有對應；(b) `humanReturnCount`、`retryHistory.gates`、`currentCount`、Bridge 投影鍵 `retry_gates` 在 SD-C 全部成品中 0 命中——最終契約新增的形狀沒有任何 AT 守。
- 座標：AT-960-4-7＝`TCS:1331-1334`；AT-960-16-E-3＝`TCS:1509-1512`；RTM 對應列＝`RTM:193`（16-E-3）。
修法：SD-C：AT-960-4-7 的 Then 與 `required` 清單補 `fsmGeneration`；AT-960-16-E-3 改用 `GET …/fsm` 的 `humanReturnCount`（刪決定表替身）、期望式改為 `retryHistory.count === FAIL 輪數(目前世代) + humanReturnCount`；新增一個 `ResearchApiIT` AT 斷言 `retryHistory.gates` 三閘 `{currentCount, entries}`、`humanReturnCount` 與 `count`／`last` 原樣不變，並補一個 pytest AT 守 Bridge 的 `retry_gates` 投影（既有 `SddFsmState.retryHistory` 有精確比對測試）。該棒：SD-C（SD-A 無需改，除非要補 `humanReturnCount` 的「目前世代」定義到 PRD）。

### F-14｜維度 2｜P3｜PRD 附錄 C 與 HELM 其餘四列有字面差異（附錄 C 以「登記主控裁決」自居）

證據（`S\qa\scan_dtext.py` rc 0、`scan_dtext3.py` rc 0）：
- D-13 WHY：PRD 加註「Architect 實測 `mobile:true` 實為 6 列＝上限，`registry.test.ts:107,143`；結論『`mobile:false`』不變」——這是對的（抽樣 #26：`mobile:true` 6 列＝上限），而 HELM 原句「`mobile:true` 已 5 項」是事實誤記（裁決層小誤，結論不變）。
- D-42 裁決：PRD 把 `W100 ≥ 8500` 寫成 `W100 ≥ 100 × 85`、`W100/100` 寫成 `W100 ÷ 100`——數值等價，但不是原文；API:165 與 AT 皆用整數 8500 比較。
- D-53 裁決：HELM「SQLSTATE 23000」、PRD「SQLSTATE 類別 23」。觸發器 `ERRCODE='integrity_constraint_violation'` 為 23000（DDL 探針 R20／R21），CHECK 違規為 23514（PostgreSQL 標準 check_violation）；TCS 若以 SQLSTATE 字串斷言須按觸發器／CHECK 分寫（我未逐 AT 核）。
- D-59 WHY：PRD 缺 HELM 括號內「SD-A 落檔判斷（主控核可）」整段（`retryHistory.gates`、Bridge 投影 `retry_gates`、`ReviewRoundDto.fsmGeneration`、`research_fetches` 第二條 CHECK）；這段是這四件事的唯一裁決出處，`API:162,172-176` 與 ARCH 已落實，PRD 附錄 C 少了回指。
修法：SD-A 附錄 C 四列同步 HELM 原文；D-13 的事實誤記由主控在 HELM 補更正一句。該棒：SD-A（＋主控改 HELM D-13）。

### F-15｜維度 9｜P4｜FRAMEWORK_VERIFY §1 步驟 7 的 `r2p_contract_check.py` 指令對「落地前」的版本目錄會得 rc 1

證據：對 `S\sdf\AISDLC_SDD\AISDLC_SDD_v0.30`（只含新檔）直接跑得 rc 1（5 項「agent_file 指向不存在的檔」，因暫存樹沒有既有 agent）；我建聯集目錄 `S\qa\vd_union\`（repo 既有 `agent/`＋`docs_template/sdd/requirements/` 複本，再覆蓋 SD-B 的 2 支新 agent 與 4 份新模板）後 rc 0。修法：SD-B 在步驟 7 註明「須在 EDITS 與新檔落地後，或對聯集目錄執行」。該棒：SD-B。

### F-16｜維度 3／9｜P4｜缺陷狀態 REGRESSED→WAIVED／SUPERSEDED 被 DDL 拒絕，審查卡模板 §5.3 對此沈默

證據：DDL 探針 D01～D10（`ddl_tests*.sql`）顯示缺陷狀態轉移矩陣如 Δ14 設計，REGRESSED 的合法出口只有 OPEN／FIXED；模板 §5.3 的缺陷狀態表未寫 REGRESSED 的合法出口。修法：SD-B 在模板 §5.3 補一句 REGRESSED 的出口，或 SD-A 放寬矩陣——擇一並寫明。該棒：SD-B／SD-A。

### F-17｜維度 3｜P4｜DDL 有四處「應用層保證」未下沉到型別層（V16～V18 發佈前補不留後遺症；視為設計選擇的建議）

證據（探針見 `S\qa\ddl_tests*.sql`）：CON01——同一專案兩筆 RUNNING 的 stage run 皆被接受（無 partial unique index）；RN01～RN03——審查輪 `round_no` 跳號不被擋（AT-960-4-7 以夾具斷言連續，但 DB 不保證）；S05——T1／T2 層證據可標 `clue_only=true`（若 PRD 的證據分層規則要求 T1／T2 不得僅作線索，應下沉為 CHECK，否則維持現狀）；DENIED 抓取列可帶空字串 host。修法：SD-A 於 Δ14 評估四項，要補就在 V16～V18 發佈前補並由 SD-C 加負控；不補則在 Δ14 寫明「由應用層保證」。該棒：SD-A（SD-C 配合）。

### F-18｜維度 9｜P4｜`FILE_DIRECTORY_RULES.md` 的「寫檔規則」表未登記四個新模板（但無既有義務）

證據：`FILE_DIRECTORY_RULES.md:401-404` 的 SDD 模板寫入位置表只列 Invariant Spec、Third-Party API Research 兩個 requirements 模板；既有的 `AMBIGUITY-WAIVER-TEMPLATE.md`、`SPEC-PATCH-TEMPLATE.md` 同樣不在表中（grep 0 命中），沒有測試鎖該表，該檔也不在 D7 白名單。四個新模板位置（`docs_template/sdd/requirements/`）與檔名（`{TYPE}-TEMPLATE.md`）、ADR 編號（`docs/02_architecture/adr/` 只有 `.gitkeep`，`ADR-001-…` 無撞號）、兩支 agent 檔名（`agent/specialized/{role}-zh.yaml`，沿 specialized 無編號慣例）、框架 TCS 路徑（`docs/03_testing/contracts/`）皆合 Rule 5 與該檔的樹。建議：主控若要完整，D7 加 `FILE_DIRECTORY_RULES.md` 並補四列；否則不動。該棒：主控裁決。

### F-19｜維度 3｜P4｜PRD 七條 AC 的 Then 只有單句（可測但貼近下限）

證據：AC-R2P-01-8、05-2、05-9、09-10、10-8、17-3、19-5（`scan_gwt.py` 判 Given→When→Then 依序皆成立；人工讀這七條，Then 皆為單一可觀察結果）。建議 SD-A 補量化門檻或錯誤碼，讓 AT 不必自行補判準。該棒：SD-A。

### F-20｜維度 2／3｜P4｜allowlist 的 `min_interval_seconds` 建立後無法調整，而 API 同句並列「PATCH 只准改 enabled」與「minIntervalSeconds 只准調高」

證據：`API:247`「`PATCH` 只准改 `enabled`（與停用欄），不可刪；`minIntervalSeconds` 只准調高（實際間隔＝max(內建下限, 條目值)…）」；DDL controlled-update 觸發器只放行 `enabled`／`disabled_*`。合讀＝「建立時的值只可高於內建下限；之後要調高須停用後重建」。建議在 `API:247` 與 AC-R2P-04-12 明寫，避免實作者以為 PATCH 可調 `minIntervalSeconds`。該棒：SD-A。

## D. 機械檢核逐字輸出

1. `python -I S\sdc\_aux\selfcheck.py` → rc=0；共 87 行（86 行 PASS＋末行 JSON），末行 `{"AC": 24, "AT": 200, "AT_pos": 158, "AT_neg": 42, "US": 3, "V": 13, "P0_covered": "111/111", "out_of_scope": 60, "rtm_rows": 228, "problems": 0}`。**它沒檢查的（我補做，見 F 節）**：AC-R2P 的期別以 PRD 重導、既有測試硬釘值（→F-01）、PRD AC 的 G/W/T、docs 閘判準以 repo 真判準重掃、audit_log 等既有行為宣稱（→F-11）。
2. `python -I -X utf8 S\sdf\apply_framework_edits.py --edits S\sdf\FRAMEWORK_EDITS.md --root <R> --check` → rc=0；末行 `apply_framework_edits：檢查 48 個編修成功、0 個失敗（涉及 13 個檔）`；`REPLACE_NUM` 現值：E02 `{#1}=59；{#2}=56；{#3}=3`、E03 21、E04 `14；5`、E07 59、E09 23、E12 `21；14；7`、E32b 59、E32c `59；56；3`、E32d 5、E33a `20；14；4；2`、E33g `14；4；2；20`、E34 23（與 VERIFY §1 步驟 3 逐值相符）。13 個目標檔全部落在 ADR-XPLAT-017 §D7 可改檔清單內（`ADR017:101`）。
3. `python -I -X utf8 S\sdf\r2p_contract_check.py <SDD 版本目錄>`：對 `S\sdf\AISDLC_SDD\AISDLC_SDD_v0.30` 直接跑 rc=1（5 項「agent_file 指向不存在的檔」，見 F-15）；對聯集目錄 `S\qa\vd_union\` 重跑：`r2p_contract_check: 9 個契約區塊、0 項問題` rc=0；`--selftest` → `r2p_contract_check selftest: 29 個注入錯誤，漏網 0；1 個合法變體，誤判 0` rc=0。
4. 自寫掃描（`S\qa\*.py`，皆 rc 0）：`scan_ids.py`（FR 23／US 23／AC 171／NFR 主項 13；懸空引用僅 NFR-R2P-03-x、08-1 為我的正則只認粗體格式的假警報；NFR 子項我手數＝45）；`scan_docsgate.py`（見 F 之 docs 閘）；`scan_coords.py`（221 筆座標、實體缺檔 0〔1 筆為範例佔位 `agent/specialized/x-zh.yaml`〕、行號超界 0）；`scan_env.py`（環境變數／SSE 事件名跨檔矩陣）；`scan_enums.py`（flow_phase／flow_status／verdict／trigger_kind／outcome 列舉對 DDL）；`scan_anchors.py`＋`scan_anchors2.py`（Architecture_delta 17 個 Δ、Console PRD delta 兩個錨點對 R 的目標檔逐一命中 1 次）；`scan_prelanded.py`（七個預先落檔檔的 LF／BOM／行數；ADR-XPLAT-016 工作樹與 ADR-XPLAT-017 的反引號路徑宣稱模擬 `TestR81GhostPathClaims`：92＋28 筆全數可解析）；`scan_cov.py`（AC-R2P 期別重導）；`scan_gwt.py`（PRD 171 條 AC 皆含 Given→When→Then 依序；TCS 200 個 AT 皆有判定指令）；`scan_dtext.py`／`scan_dtext2.py`／`scan_dtext3.py`（PRD 附錄 C 對 HELM：HELM 48 列、PRD 58 列、差異 6 項，見 F-12／F-14）；`scan_fwtcs.py` 輸出逐字：`AT 定義數 33 唯一 33`、`負控(E) 9 正控 24`、`映射列數 33 AT 覆蓋 33`、`Show-Result 次數 33 涵蓋 AT 數 33`、`懸空 AC-R2P [] 懸空 FR-R2P []`、`D 引用越界 []`。
5. D-48 殘留搜尋：模式「INIT、SPEC_FIRST_GATE、BRIDGE」掃 `sd`、`sdf`、`sdc` 全部 md → 2 命中：`ResearchToPRD_PRD.md:1670`（過期，F-12）、`FRAMEWORK_VERIFY.md:243`（SD-B 自己指出差異的原話，非缺陷）；`TCS-Framework:32`、`:1147`、`:1153` 逐一列出的三份檔（`AISDLC_SDD/CLAUDE.md`、INIT、SPEC_FIRST_GATE）與「BRIDGE 不在採納集合」皆符合 HELM 現行 D-48。
6. DDL：`docker exec autoclaude_pg psql … -f V1…V19`（拋棄式庫）全數 rc 0；18 張 `research_*` 表、每張皆掛 `research_append_only_guard` 或 `research_controlled_update_guard`（查 `pg_trigger` 無漏）；探針結果摘要：D-59 的 CHECK 對 NULL 皆擋（S02、F02、F03、V02〔349526 個中文字＝1048578 位元組被拒〕）；輪表 R02／R03／R05／R07／R10～R13／R16 皆被對應 CHECK 擋；R20／R21 append-only 拒（SQLSTATE 23000）；缺陷狀態 D01～D10 轉移矩陣如設計（REGRESSED→WAIVED／SUPERSEDED 被拒，見 F-16）；專案表 P01～P08；allowlist A01～A08（`notreddit.com`、`redd.it.example.com` 不被 Reddit 規則誤傷）。探針 E01 初見「ACCEPTED」只因表為空（列觸發器未觸發），補資料後重測為 REJECTED（不是缺陷）。
7. 既有行為現查（F-01、F-10、F-11 的依據，皆為讀檔）：`test_doc_loc_baseline_freshness_r60.py:3948-3958`（幽靈路徑掃描面）、`V6__audit_log.sql:6-17`、`AuditLogWriter.java:29-30`、`AuditLoggingFilter.java:32-34,63-93`、`RequestAuditTrail.java:42-59`、`AuditPersistenceApiIT.java:76-88`；四個 Flyway 版本清單 IT、`OpenApiIT.java:247`、`si.endpoints.test.ts:44-47`。
8. `python -I -X utf8 S\qa\scan_report.py <本報告>`（docs 閘嚴格判準、斜線對、磁碟絕對路徑、日曆承諾、雜湊字樣）→ rc=0；LF 行尾、無 BOM；五項命中數皆為 0。

## E. 座標抽樣表（≥30）

全部 221 筆座標已機械驗證「檔存在、行號在範圍內」，內容逐筆抽樣如下（皆指向 R 的現況工作樹）。

| # | 引用（文件） | 實際行內容（R） | 一致 |
|---|---|---|---|
| 1 | `sdd_cli.py:61-74`（ADR017:10） | `ALLOWED_VERBS: frozenset[str] = frozenset({ VERB_SPEC_FROZEN, VERB_NEGOTIATE_ENTER, …` | ✓ |
| 2 | `sdd_cli.py:165-167`（ADR017:46） | `def build_cli_argv(...)` → `…"--project", project, "--must-exist", *args]` | ✓ |
| 3 | `routers/sdd.py:313-316`（ADR017:16） | `if not any(_TCS_NAME.match(posixpath.basename(d)) for d in docs): raise unprocessable([{ "field": "docs", "rule": "missing_tcs"` | ✓ |
| 4 | `routers/sdd.py:336`（PRD:628） | `@router.post("/fsm/{project}:freeze")` | ✓ |
| 5 | `routers/sdd.py:382-387`（ADR017:42） | `def _state_root_of(spec_dir)…自 spec_dir 向上找第一個含 build/reports/fsm 的目錄` | ✓ |
| 6 | `transition_rules.py:12-35`（ADR017:10） | `_HAPPY_PATH: Dict[str, Set[str]] = {` … `"SPEC_FROZEN": {"IMPLEMENTATION","SPEC_DRAFTING","TEST_CONTRACT_NEGOTIATED"}` | ✓ |
| 7 | `transition_rules.py:267-275`（PRD:1348） | `RETRY_LIMITS … "SCG_VALIDATION": 3,` | ✓ |
| 8 | `transition_rules.py:305-326`（ADR017:10） | `next_state_on_gate_pass`／`next_state_on_gate_fail`（`current_count >= limit → ESCALATION`） | ✓ |
| 9 | `transition_rules.py:46,66,68`（PRD:787） | IMPLEMENTATION／PR_REVIEW／RTM_VERIFY 的出邊列，皆無 SPEC_DRAFTING | ✓ |
| 10 | `transition_rules.py:156,160`（WF:206） | `"ESCALATION": {…}`、`"RESUME_VERIFICATION": {"SPEC_DRAFTING","IMPLEMENTATION","PR_REVIEW","ESCALATION"}` | ✓ |
| 11 | `fsm_runtime.py:526-645`（PRD:582） | `def record_gate_result(self, gate, result, reason="")`…`gate_fail_blocked`（:628-641） | ✓ |
| 12 | `fsm_runtime.py:596-620`（ADR017:69） | `W-15-1 / B-axis L4：flag-gated 有界自動恢復接入` | ✓ |
| 13 | `fsm_runtime.py:3431`（ADR017:53） | `_STRUCTURED_VERBS = (*_BRIDGE_VERBS, "spec-refreeze")` | ✓ |
| 14 | `fsm_runtime.py:3684-3700`（ADR017:51-52） | `elif args.command == "transition":`／`elif args.command == "gate":`（舊動詞，非單行 JSON 契約） | ✓ |
| 15 | `fsm_runtime.py:328-336`（WF:117） | `_STATES_ALLOWING_SPEC_WRITE = {SPEC_DRAFTING,…,AGENT_LOAD}` | ✓ |
| 16 | `state_loader.py:305-308`（ADR017:75） | `# Reset current_count for every gate…for gate_name in ("SCG_VALIDATION","PR_REVIEW","RTM_VERIFY","RELEASE_READY")` | ✓ |
| 17 | `SDD_FSM_ENGINE.md:374-378`（PRD:1444） | `HUMAN_PENDING｜人工確認通過，但本 Stage 有重試歷史（current_count > 0）｜SPEC_REGRESSION_CHECK` 等列 | ✓ |
| 18 | `SDD_SPEC_FIRST_GATE.md:194`、`:210-213`（PRD:1672） | 第 5 列「維持 HUMAN_PENDING（FSM 沒有 HUMAN_PENDING → SPEC_DRAFTING 的邊）」；SPEC_REGRESSION_CHECK 條 | ✓ |
| 19 | `SDD_FSM_ENGINE.md:433-434`（PRD:593） | `HUMAN_PENDING｜timeout = 72h｜REMINDER`／`168h｜ESCALATION` | ✓ |
| 20 | `.claude/hooks/session_start.py:279`（PRD:593） | `# ACT-023: HUMAN_PENDING wall-clock timeout check (72h reminder / 168h escalate).` | ✓ |
| 21 | `db.py:12-13`（PRD:439） | `全部是 best-effort：DB 掛了／列不存在／FK 不成立都只記 log 並回 False` | ✓ |
| 22 | `db.py:100-114`（ARCH:120） | `if updated is False: logger.info("execution_runs 列不存在…跳過狀態鏡射")` | ✓ |
| 23 | `security.py:275`（PRD:490） | `def check_outbound_url(url, allowlist) -> tuple[bool, str, str]:` | ✓（語意見 F-05） |
| 24 | `security.py:35`（PRD:1301） | `DENY_CHARS: frozenset[str] = frozenset("!`><~$&;")` | ✓ |
| 25 | `config.py:188`（PRD:894） | `step_timeout_seconds: int = 600` | ✓ |
| 26 | `lib/nav/registry.ts:42-115`（ARCH:84） | 九列；`mobile:true`＝dashboard、projects、import、execute、monitor、settings＝6；order 10／20／30／40／50／80／70／55／75（35 空缺） | ✓ |
| 27 | `lib/nav/registry.test.ts:107,143`（PRD:830） | `if (registry.filter((e) => e.mobile === true).length > 6) out.push({ kind: "mobile-overflow"…` | ✓ |
| 28 | `lib/help/registry.ts:67`（PRD:1180） | `export const PENDING_HELP_PAGES: readonly HelpId[] = [];` | ✓ |
| 29 | `SecurityConfig.java:86-99`（TCS:1742、ARCH:138） | `:86` GET→VIEWER+；`:88` SI POST ADMIN；`:91-92` issues PUT／DELETE；`:95` sysadmin POST；`:96` settings；`:97` 通用 OPERATOR+ | ✓ |
| 30 | `test_sdd_cli.py:222-230,274-275`（TCS:1749） | `transition`／`gate`／`show`… 越界清單；`assert sdd_cli.ALLOWED_VERBS == {…五個}` | ✓ |
| 31 | `test_sdd_freeze.py:336`（TCS:1750） | `assert resp.json()["violations"][0]["rule"] == "missing_tcs"` | ✓ |
| 32 | `endpoints.test.ts:204`（TCS:1731） | `expect(names).toHaveLength(84);` | ✓（但見 F-01-3） |
| 33 | `OpenApiIT.java:145,153,169`（TCS:1740） | `hasSize(77)`／`isEqualTo(89)`／`hasSize(77)` | ✓（但 `:247` 漏列，F-01-2） |
| 34 | `SchemaMigrationIT.java:63-68`（TCS:1739） | `containsExactly("1",…,"15")`（`:68`） | ✓（另四檔漏列，F-01-1） |
| 35 | `docker-compose.yml:227`（PRD:1178） | `BRIDGE_DB_DSN: postgresql://…`（`BRIDGE_ALLOWED_PATH_ROOTS` 實在 `:230`） | ✗（F-03） |
| 36 | `rtm_backfill_W7FE.md:5`（PRD:592） | `20KB 預覽更新中位數 129ms → 58ms` | ✓ |
| 37 | `tools/lib/unattended_authz.py:40-44,57-61`（PRD:1191） | `#: 無人回合的時間邊界（DEF-200-575…` | ✓ |
| 38 | `test_root_module_layout.py:140-146`（PRD:1707） | `def prd_problems(repo_root)`（含「模組落點表」字樣須引 SSOT） | ✓（PRD 含字樣且引 SSOT） |
| 39 | `V13__si_console_writes.sql:28-51`（PRD:1182） | `CREATE FUNCTION console.si_console_writes_guard() RETURNS trigger` | ✓ |
| 40 | `ImportController.java:108-116`（ARCH:791） | `@PostMapping("/{id}/parse")`（三條路徑擇一） | ✓ |
| 41 | `V6__audit_log.sql:6-17`（對照 PRD:474／484、API:247、ARCH:223 的 `note` 宣稱） | 欄位清單 `id, occurred_at, subject, role, method, path, entity_type, entity_id, http_status, trace_id`，無 note／action | ✗（F-11） |
| 42 | `AuditLoggingFilter.java:32-34、:82-85、:91-92`（對照 TCS:1364 的「403／422 不增列」） | 注解「被拒絕的寫入（401／403／429）同樣會留下審計紀錄」；`entry.put("action", action)` 只進日誌行、落庫 `Entry` 無 action | ✗（F-11） |
| 43 | `AuditPersistenceApiIT.java:76-88` | `rejectedWritesAreRecordedWith…`：VIEWER 刪除回 403 → 一列 `http_status`＝403；匿名 401 → 一列 `subject`＝null | ✗（與 AT-960-5-4 互斥，F-11） |
| 44 | `FILE_DIRECTORY_RULES.md:401-404`（維度 9 判準） | 寫檔規則表只列 Invariant Spec、Third-Party API Research；既有 AMBIGUITY-WAIVER／SPEC-PATCH 亦未列 | ✓（F-18 為 P4） |
| 45 | `ADR017:101` 可改檔清單 ↔ `FRAMEWORK_EDITS.md` E01～E36 的 13 個目標檔 | INIT、workflow/README、agent/specialized/README、SDD_SPEC_FIRST_GATE、BRIDGE、兩個 scenarios、`AISDLC_SDD/CLAUDE.md`、EVOLUTION_LOG、CHANGELOG、docs_template/README、agent/README、PROJECT_DOCUMENTATION_STANDARDS 全在清單內 | ✓ |
| 46 | `AISDLC_SDD_v0.30/docs/02_architecture/adr/`、`docs/03_testing/contracts/` 現況 | 兩目錄僅 `.gitkeep`，`ADR-001-…` 無撞號；`AISDLC_SDD/CLAUDE.md:219-230`（Rule 5）命名皆合 | ✓ |
| 47 | `test_doc_loc_baseline_freshness_r60.py:3948-3958`（F-10 的掃描面判準） | `_PATH_CLAIM_GLOBS`＝`ONBOARDING.md`、兩份 `CrossPlatform_*`、`*HANDOFF*.md`、`docs/04_planning/ADR/*.md`、`AutoSDD_improving_*.md`（根 `CLAUDE.md` 另處理） | ✓（確認不含 `docs/01_requirements/`） |

## F. 覆蓋重數

- **FR／US／AC／NFR**：FR 23、US 23、AC 171（`AC 每 FR 數` 序號連續、無重號）、NFR 主項 13／子項 45（我手數：03×7、04×5、05×4、06×5、07×4、08×5、10×4、11×3、12×5、13×3＝45）；與 `ID_INDEX.md` 逐項相符。
- **來源規格 §1～§7 → FR 承接**：附錄 A（PRD:1466-1505）逐列重驗；§2 目錄、§3.1 三層、§3.2 六節、§3.3 四審查（權重 30／25／25／20、W100 算例我手算 7990／8830／8495／8500 皆對）、§4 雙軌表、§5 十四個狀態、§6.1 頂列與五項側欄、§6.2 五頁（含「`[開啟本地專案]`」「`[一鍵自動迭代修正]`」「優缺點矩陣」「檢索深度開關」各有 FR 落點）皆有 FR／AC；被「依設計改寫」者皆附裁決與再開症狀：§5 的「≤3 次修訂」→D-24（3 輪）、§2 的「根目錄 my-project/」→D-28（repo 外）、§6.2 WebSocket→SA-04（SSE）、§6.1 五個並列入口→D-13（單一入口）、頂列全域狀態列→D-31（工作流內 Header）、SA-08「改名」→D-40（複製保留）。**覆蓋無缺口。**
- **P0 AC-R2P 覆蓋 n／n**：selfcheck 的 111／111 以 TCS 自己的 §1.2／§1.3 分割為準；我以 PRD FR 標題期別重導（`scan_cov.py`）：FR-01～10、21～23 為 P0 或隨期擴充，FR-11～17、20 為 P1／P2，FR-02／18／19 混期；§1.2 的 111 列中**沒有任何一條屬純 P1／P2 的 FR**，§1.3 的 60 列中屬 P0 起 FR 的只有 AC-R2P-18-2／18-3（FR-18 類型 b～d＝P2，TCS 已標）；FR-19 八條全屬 P1／P2（正確排除）。部分覆蓋者（AC-R2P-01-5、02-4、02-5）TCS 以⚖2／⚖3 逐項說明。**重數結論：111／111 成立**（但覆蓋≠AT 殺傷力，見 F-01、F-02、F-11、F-13 對 AT 的補洞）。
- **TCS AT 數**：200（正控 158／負控 42；pytest 103、JUnit 37、vitest 44、Playwright 6、指令核對 10；皆有 Given／When／Then 與判定指令）；V 系列 13；RTM 228 列＝F 1＋US 3＋AC 24＋AT 200（selfcheck 與我獨立計數一致）。
- **框架 TCS**：33 個 AT（正控 24／負控 9；AC-970-1～7 皆有 AT；§1 映射表 33 列＝33 個 AT；每個 AT 皆有 `Show-Result`；懸空 AC-R2P／FR-R2P 0；D 引用越界 0，`scan_fwtcs.py`）；`FRAMEWORK_EDITS` 48 塊／13 檔皆在 D7 白名單內；新增九檔路徑與命名合 Rule 5 與 `FILE_DIRECTORY_RULES.md` 的樹（F-18 為 P4 建議）。
- **docs 閘**（真判準＝`tools/check_pytest_baseline_sites.py`：同一行出現 passed 或 skipped（不分大小寫）且同行有千分位數字或 4 位以上整數；斜線對形態另判）：落檔面（PRD、ADR-003、ADR-XPLAT-017、API 契約、Architecture_delta、計畫書、TCS、RTM）0 命中；框架樹檔 `AISDLC_SDD_v0.30/docs/03_testing/contracts/` 下的框架 TCS 第 72 行有 1 命中，但 `AISDLC_SDD/AISDLC_SDD_v` 是該閘的豁免樹（`_DATED_ARTIFACT_PREFIXES` 第一列），不計；磁碟絕對路徑 0（TCS 內 Windows 風格的路徑字樣是測試輸入範例字串，非檔案路徑宣稱）；日曆承諾 0（PRD 內 Q 開頭字樣皆為問題編號、非季度）；CRLF 0；`AgentConsole/CLAUDE.md` 167 行。**本報告自身**也以同一判準重掃，0 命中。

## G. 誠實劃界

1. **沒有逐行讀完的部分**：PRD 171 條 AC 只機械驗 G/W/T 結構並抽讀約 40 條的語意；ADR-003 D15～D16、Plan §3～§8、API 契約各端點錯誤碼表只做跨檔 token 矩陣；SD-C 的 200 個 AT 深讀約 25 個，其餘只驗結構、判定指令存在與 ID／AC 映射；框架 workflow §3～§7／§11～§14、兩支 agent YAML、`FRAMEWORK_EDITS` 多數塊只驗 `--check` 命中與 13 檔白名單；框架 TCS 33 個 AT 與其內嵌檢核器本體只驗結構與 `Show-Result`，AT-970-7-x 的 FSM 演練**沒有實跑**（任務書禁寫入動詞）。
2. **沒跑的檢核**：`arch_fitness`、各 lint、`ci-gate`、TLC、vitest／gradle／pytest 與 repo 內任何 unittest（規格階段沒有生產碼，且 repo 唯讀）；`test_root_module_layout.py::prd_problems` 只讀碼推演（#38），未實跑。
3. **DDL** 只在本機 PG18 容器的臨時庫驗過（用畢已丟），僅 Windows，未驗其他 PG 主版本；66 個探針是我對 Δ14 與 D-42／D-50／D-55／D-57／D-59 的理解所設計，非窮盡。
4. **座標**：221 筆全數驗「檔存在、行號在範圍內」，內容抽樣 47 筆，不保證每行內容。**硬釘值掃描**（F-01）只涵蓋 Flyway 版本清單、`hasSize(77|89)`、`toHaveLength(84)` 三族，不保證窮盡；**既有行為核對**（F-11）只針對 `audit_log` 一條，其餘「既有行為宣稱」（例如 `retryHistory` 精確比對測試、`check_outbound_url`）只核了 F-05、F-13 所列。
5. **安全維度**（SSRF／allowlist、權杖、RBAC、核准只認 JWT subject、headless `--allowedTools`、第三方原文不進版控）以抽樣與跨檔矩陣為主，沒有對每條 AC 做威脅建模；發現限於 F-05。
6. **嚴重度是判斷**：F-01、F-11 最接近 P1，我判 P2 的理由見 B；主控若升級，結論（FAIL）不變。
7. **時效**：審查基準＝HEAD `01d9be6e` 加未 commit 的 M／??；審查期間若 `S\sd`、`sdf`、`sdc` 或 repo 工作樹再變動，以複審為準。只讀了 `AISDLC_SDD_v0.30`（框架檔頭自稱的 LATEST），未驗其他歷史版本。
8. **獨立性**：多個 SD 一致的說法（例如「`note` 標在 audit_log」「恢復後可繼續修訂」）我都回上位程式碼與既有測試重驗，F-02、F-11 即由此而來；SD 自報的計數（selfcheck、ID_INDEX、VERIFY）皆自己重跑或重數。

## 進度：已完成維度／未完成維度

- 已完成：維度 1～9 全數完成（深度見 G：維度 2、7、8 機械全掃；維度 1、3、4、5、6、9 為抽樣加關鍵點深驗）。
- 未完成：無。報告定稿並已交卷（一審）。

## H. 二審

> 二審範圍（主控指令）：F-01～F-20 修法落實逐條（P2 四條逐字驗）＋本輪新增／改寫區域的增量審查＋可低成本重跑的 DDL 探針。二審基準＝三棒修訂後的 `S\sd`、`sdf`、`sdc` 現稿與 HELM 的 D-60～D-64。座標一律指向現稿（`PRD`＝`ResearchToPRD_PRD.md`、`ARCH`＝`Architecture_delta.md`、`TCS`＝P0 測試契約、`FW_TCS`＝框架 TCS、`WF`＝工作流主檔、`T_CARD`＝審查卡模板）。

### H.1 逐條 F 落實表

| F | 一審嚴重度 | 二審狀態 | 新座標與逐字證據 |
|---|---|---|---|
| F-01 | **P2** | **部分落實**（殘餘＝F-21） | `TCS:1792`（#10）、`:1800`（#13）、`:1801`（#14）、`:1829`（E7）、`:1837-1841`（#24～#28）、`:1904`／`:1908`／`:1909`（§5.7）；`sdc\_aux\HARDPIN_SCAN.txt`。#13「五個既有 IT 的 Flyway 版本清單：…`IssuePriorityMigrationIT.java:130-131`、`BackupJobMigrationIT.java:167-168`…、`SiConsoleWritesMigrationIT.java:128-129`」、#14「路徑數 77 改 101（`:145`、`:169`、`:247` 三處同改）、操作數 89 改 115」、#10「`si.endpoints.test.ts:46` 的字串同步為 `expect(names).toHaveLength(109);`…兩檔必須由同一個包同時改，只改一邊必紅」、E7「**需改測試**」；§5.7 的 PKG-DB、PKG-API、PKG-FE-A 允許集合皆已納入。重掃八組（A Flyway、B OpenApiIT 計數、C 後端集合鎖、D 前端 lib、E 前端 tests、F Bridge 鍵集合、G Bridge 全樹掃描器、H 前端靜態測試）與新增 #24（Bridge `_NEW_KEYS` 加 `retry_gates`）、#25（SI reason 表解析）、#26（`ErrorReasons` 前綴鎖）、#27（`app/` 全樹 AST 與文字鎖）、#28（前端靜態鎖）皆在位。我的獨立掃描（H.3 第 7 項）核對前端 components／tests／lib 長度與計數釘選、Bridge 的 openapi 與 routes 釘選、框架 count-drift 測試，皆無遺漏；**唯一遺漏是 `BackupJobMigrationIT.java:154` 的前後快照相等斷言（→F-21）**。 |
| F-02 | **P2** | **落實** | 六處語意一致，見 H.1.1 對照表。引擎事實我重讀驗證：`state_loader.py:237-248`（計數已達上限時 `current = limit` 並標「tamper detected: prior_count=… ≥ limit=…」）、`fsm_runtime.py:535-544`（PASS 才 `reset_retry`）、`:576-595`（FAIL 達上限走 ESCALATION 分支）、`:642-644`（回傳 `retry_count`、`next_state`、`escalated`）、`:1194-1218`（`resume_from_escalation` 不動計數）。 |
| F-03 | P3 | 落實 | `PRD:972`「`docker-compose.yml:230、260–295`」、`PRD:1190`、`ADR003:100`「`docker-compose.yml:230`」；現檔 `AgentConsole/docker-compose.yml:230` 為 `BRIDGE_ALLOWED_PATH_ROOTS: /workspace`，`:260` 起為 `- type: bind`、`:293` 為最後一個唯讀 bind 的 `read_only: true`。 |
| F-04 | P3 | 落實 | `PRD:269-272`（§5.1.3 預檢代碼表四列：`CITES_MISSING`、`CITES_V1`、`CITES_UNANCHORED`、`CITES_CANDIDATE`）、`PRD:513`（AC-R2P-05-2「代碼名取 §5.1.3 預檢代碼表」）、`PRD:564`、`T_PRD:42`（P0-7 列「…（否則 `CITES_MISSING`）…（否則 `CITES_V1`）…（否則 `CITES_UNANCHORED`）…（否則 `CITES_CANDIDATE`）」）、`TCS:947` 同名。 |
| F-05 | P3 | 落實（用語殘餘→F-23） | `PRD:480,490,501,912`「檢查函式為包裝 `check_research_url`——先呼叫既有 `check_outbound_url` 取 parser 一致性，再加 https 限定、埠 443 限定、尾點拒絕與解析後私網 IP 拒絕，不修改 `check_outbound_url`」、`ADR003:80`、`ARCH:164`；`PRD:1589` 的 D-35 列保留原文並附 D-62(3) 訂正。 |
| F-06 | P3 | 落實 | `PRD:1224,1278`、`ADR017:137`、`ARCH:855`、`PLAN:44,177` 皆為 `ResearchSchemaMigrationIT`（「既有 `SchemaMigrationIT` 只改 Flyway 版本清單」）。 |
| F-07 | P3 | 落實 | `PRD:793`「（資料表隨 V19〔P1〕）」。 |
| F-08 | P3 | 落實 | `PRD:810`（AC-R2P-19-8：依序 `transition →SPEC_AUDIT`、發佈新 PRD、`spec-refreeze`、`transition →PR_REVIEW`、`gate PR_REVIEW FAIL`；現態矩陣；回傳不是 IMPLEMENTATION 即 `BLOCKED`；現態不在矩陣內 409 `fsm_state_conflict`）、`ADR017:156-157`。FSM 邊逐條核：`transition_rules.py:46`（IMPLEMENTATION→SPEC_AUDIT）、`:67`（SPEC_AUDIT→PR_REVIEW）、`:66`（PR_REVIEW→IMPLEMENTATION）、`:68`（RTM_VERIFY→IMPLEMENTATION）、`:77`（RELEASE_READY→IMPLEMENTATION）；RELEASE_READY FAIL 的 `--reason` 必填（`fsm_runtime.py:528-533`）與 `ADR017:157`「後者 --reason 必填」一致。 |
| F-09 | P3 | **部分落實**（threshold 與三條 CHECK 落實；`floor_score` 未鎖→F-22） | `ARCH` 的 V18：`threshold … CHECK (threshold BETWEEN 50.00 AND 100.00)`、`CHECK ((verdict = 'PASS') = (passed IS TRUE))`、`CHECK (escalated = (verdict = 'ESCALATE'))`、`CHECK ((fsm_retry_count IS NULL) = (fsm_gate_result IS NULL))`；`escalated`、`verdict`、`passed`、`threshold` 皆 NOT NULL，所以三條不會被 NULL 靜默放行。資料庫探針（H.3 第 5 項）：一審被接受的 R01、R06、R14、R15 現在皆 REJECTED（CHECK 違反；SQLSTATE 見 H.3 第 5 項），T01 以 `research_review_rounds_threshold_check` 單獨擋下 threshold＝0。注意：一審的 R17 現在雖也被擋，但擋它的是 `…_check8`（retry 為 NULL），不是 threshold 鎖，所以我另寫 T01 隔離驗證。 |
| F-10 | P3 | 落實 | `PLAN:31`（W0 表新增一列，檔欄為 `docs/01_requirements/ResearchSOPtoPRD_Source_Spec.md`，內容欄「來源規格逐字檔…**主控預先落檔、W0 同 commit 收入**（落檔 commit 一併 `git add`…」）、`PRD:1165`（§9.0 落點表同列）。 |
| F-11 | **P2** | **落實** | `PRD:485`、`PRD:495`（AC-R2P-04-7：「console-api 以既有 `AuditTrail.note("research.allowlist", "research_allowlist", <條目 id>)` 標註：該請求的 V6 `audit_log` 列（本就恆一列）`entity_type='research_allowlist'`、`entity_id`＝條目 id、`subject`＝JWT subject、`role`＝ADMIN、`http_status`＝201（停用為 200），`audit` 日誌行帶 `action=research.allowlist`」「Given OPERATOR／VIEWER 新增 Then 403…`audit_log` 仍恰多一列（`http_status` 為 403；既有過濾器對被拒的寫入照留紀錄，V6 無 `note` 欄，AT 不斷言 `note`）」「422 `terms_ack_required`，同樣恰多一列（`http_status` 為 422）」）、`API:250`、`ARCH:225`、`TCS:1397-1401`（AT-960-5-4：「V6 `audit_log` 沒有 `note` 與 `action` 欄，`action` 只以日誌行斷言；D-62(1)」「每個 `/api/` 寫入請求恆多一列，與有無標註無關」「OPERATOR 與 VIEWER 回 403 亦各多恰一列（`http_status` 為 403…）、迷你 Bridge 請求數為 0」）、`TCS:1968`（⚖）、`HELM_DECISIONS.md:62`（D-62(1)：「**不新增欄位、不改 V6、不改 `AuditLoggingFilter`**；AT 不得斷言「403／422 不增列」或 `note` 欄」）。對照現碼（本輪重讀）：`V6__audit_log.sql:6-17`（無 note／action 欄）、`AuditLogWriter.java:29-30`、`AuditLoggingFilter.java:32-34,82-85,91-92`、`AuditPersistenceApiIT.java:76-88`（被拒寫入留列）——新文字與現碼一致。歷史列 `PRD:1464` 仍記 rc2 當時的 `note=research.allowlist`，緊接的 `PRD:1465` 記 D-62(1) 訂正，屬變更紀錄的時序，不是矛盾。 |
| F-12 | **P2** | **落實** | `PRD:1683`（附錄 C 的 D-48）：「(1) 框架鍵適用增量（delta）條款：Stage-1 採納的三份上位文件（BRIDGE §8.4 `sdd` 列＝`AISDLC_SDD/CLAUDE.md`、`AISDLC_SDD_INIT.md`、`SDD_SPEC_FIRST_GATE.md`；SD-B 修訂交卷指正，原寫 BRIDGE 有誤）的改動＝只增不減的註冊與條文增補，收尾對這三份 `spec-refreeze`；BRIDGE 不在凍結集合、同樣只增不減」，與 `HELM_DECISIONS.md:48` 逐字相同（`scan_dtext2.py`：HELM 393 字／PRD 393 字、無差異）；同時 D-13（`PRD:1567`）、D-59（`PRD:1694`）的 HELM 對照亦已逐字相同。 |
| F-13 | P3 | 落實 | `TCS:1362-1365`（AT-960-4-7 加 `fsmGeneration` 必填與 `fsmRetryCount` 逐值）、`TCS:1367-1370`（AT-960-4-8：`retryHistory.gates` 三閘 `{currentCount, entries}`、`humanReturnCount` 只數目前世代）、`TCS:1555-1558`（AT-960-16-E-3 改用 `retryHistory.gates.SCG_VALIDATION.entries` 與 `humanReturnCount`，「沒有另外的決定表端點」）、`TCS:1139-1142`（AT-960-13-9：Bridge `retry_gates`）。六組（甲～己）我逐組代入「`entries` ＝ 目前世代 FAIL 輪數 ＋ `humanReturnCount`」：甲 2＝2＋0、乙 2＝1＋1、丙與丁警示、戊 1＝0＋1、己 1＝1＋0，成立。 |
| F-14 | P3 | 落實（D-42／D-53 仍改寫，已附揭露） | D-13、D-48、D-59 現與 HELM 逐字相同；D-42（`PRD:1677`）、D-53（`PRD:1688`）仍把數字詞改寫，但列尾加「〔原文逐字見 HELM；本列為避開判準改寫數字詞〕」，偏離已具名、有 WHY。 |
| F-15 | P4 | 落實 | `FRAMEWORK_VERIFY.md:95`「**前置（QA 一審 F-15）：須在步驟 2（新增檔）與步驟 3（既有檔編修）落地之後，對 `$vd` 執行；落地之前要先檢，就對下面的聯集目錄執行。**」與 `:105` 的聯集目錄指令。我重跑：聯集目錄 rc 0、sdf 暫存樹 rc 1（5 項），與該段所述相符。 |
| F-16 | P4 | 落實 | `T_CARD:191`「`REGRESSED`…合法出口只有 `FIXED`…不得直接轉為 `OPEN`、`WAIVED` 或 `SUPERSEDED`」、`T_CARD:195`（整張轉移矩陣：`OPEN`→`FIXED`／`WAIVED`／`SUPERSEDED`；`FIXED`→`REGRESSED`；`REGRESSED`→`FIXED`；`WAIVED`、`SUPERSEDED` 為終態）；DDL 觸發器 `ARCH:693-694` 同矩陣；`FW_TCS:676`（AT-970-6-1 斷言）；`HELM_DECISIONS.md:63`（D-63）。**更正一審**：我在一審 F-16 把 REGRESSED 的出口寫成「OPEN／FIXED」是轉述錯誤——一審抽出的 DDL（`qa\ddl\V18…sql:112-119`）與 D-49(3) 一直只放行 REGRESSED→FIXED，我當時實際發現的只是「模板 §5.3 對 REGRESSED 的出口沈默」；SD-B 與主控依 DDL 與 D-49(3) 處理是對的。二審探針 D08、D09 仍 REJECTED、D10 ACCEPTED，與矩陣一致。 |
| F-17 | P4 | 落實 | `ARCH:415`（`CREATE UNIQUE INDEX ux_research_stage_runs_active ON console.research_stage_runs (research_id) WHERE status IN ('QUEUED','RUNNING')`，D-61）、V17 的 `CHECK (host IS NULL OR host <> '')`、`ARCH:462`（T1／T2 的 `clue_only`「不下沉為 CHECK（D-61：應用層保證、AT 守）」）、`ARCH:600`（「round_no 連續…由 Bridge 寫入器於同交易 max+1 配號保證、AT 守（D-61）」）。探針：CON01 現為 REJECTED [23505] `ux_research_stage_runs_active`、F06（DENIED 列的空字串 host）現為 REJECTED（`research_fetches_host_check`）；RN01～RN03 與 S05 仍被接受，與「應用層保證」的明文一致。 |
| F-18 | P4 | 落實（以裁決處置） | `HELM_DECISIONS.md:62`（D-62(4)「不開白名單」）、`FRAMEWORK_EDITS.md:481`（E30 的〈已知邊界〉格：「`FILE_DIRECTORY_RULES.md` 寫檔規則表未登記四個新模板（既有兩模板同樣未登記，框架既有債）」）、`FRAMEWORK_VERIFY.md:208`。 |
| F-19 | P4 | 落實 | 一審點名的七條 AC 的 Then 皆已補量化或可觀察條件：AC-R2P-01-8（`PRD:424`「導回游標所在步…發出的寫入請求數為 0」）、05-2（`PRD:513`）、05-9（`PRD:520`「SQLSTATE 23000…`research_events` 列數不變」）、09-10（`PRD:615`「71.99 小時顯示「已等待 71 小時」且無橫幅，72.00 小時…」）、10-8（`PRD:636`「`decision_trace` 依序恰出現…」）、17-3（`PRD:772`「`script` 元素 0 個…哨兵呼叫次數為 0」）、19-5（`PRD:807`「`violations[]` 每項違規一筆…」）。我的長度啟發式仍標 09-10，但它的 Then 是多子句量化句，屬啟發式誤報。 |
| F-20 | P4 | 落實 | `API:250`「body 含 `enabled` 以外的欄位（含 `minIntervalSeconds`）回 422 `invalid_request`、條目不變；`minIntervalSeconds` 建立時決定、**建立後不可 PATCH**…要調整間隔＝停用該條目後重建」、`PRD:500`（AC-R2P-04-12 同句）、V17 欄位註解「建立後不可改（受控更新守衛只放行 enabled／disabled_*），要調整＝停用後重建」。 |

#### H.1.1 F-02 六處語意對照（D-60）

語意六點：（a）人工恢復不動計數；（b）恢復後至多再得一次審查；（c）該輪通過＝歸零並轉 HUMAN_PENDING；（d）該輪未過＝立即再 ESCALATION（歷史列帶引擎的 tamper 字樣＝已知邊界）；（e）全新預算＝換世代鍵（僅 ADMIN）；（f）UI 剩餘預算＝`max(0, 3 − currentCount)`，恢復後顯示 0 並標「恢復後僅一次機會」、按鈕仍啟用。「—」＝該處不需承擔。

| 處 | 座標 | a | b | c | d | e | f |
|---|---|---|---|---|---|---|---|
| PRD | `PRD:571,584,597,610,778,790` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| ADR-XPLAT-017 §D6 | `ADR017:27,91-99`（`:95-97` 三列表：恢復後 `3（不變）`／通過 `歸 0`／未過 `3（夾在上限）→ESCALATION（立即…L-R12）`） | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| API-RP-11 | `API:230,318` | ✓ | ✓ | ✓ | ✓ | ✓（`:246`） | ✓ |
| 工作流 §2.5 | `WF:170-171` | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| 審查卡模板 §2.3 | `T_CARD:74` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| TCS 13-8（真 CLI 實跑） | `TCS:1134-1138` | ✓ | ✓ | ✓ | ✓ | — | — |
| TCS 12-E-5（兩入口對拍） | `TCS:1094-1098` | ✓ | ✓ | ✓ | ✓ | — | ✓（「不因剩餘預算算成 0 而零輪」） |
| 框架 TCS 7-6 | `FW_TCS:987-1021`（斷言常數 `:688`、`:700-701`） | ✓ | ✓ | ✓ | ✓ | ✓ | — |

引擎對照：框架 TCS 的預期值「`retry_count=3`（不是 1，也不是 4）、`next_state=ESCALATION`、`escalated=True`，歷史末列的 `failure_reason` 帶 `tamper detected: prior_count=3`；第二次恢復後的 `gate PASS` 回傳 `next_state=HUMAN_PENDING` 且計數歸 0」與 `state_loader.py:237-248`、`fsm_runtime.py:535-544,576-595,642-644` 讀碼推演逐項吻合（`RESUME_TARGETS` 含 SPEC_DRAFTING：`fsm_runtime.py:41`；`resume-from-escalation`、`--must-exist`、`--reason` 旗標：`:3654,3725-3731`）。

### H.2 增量發現

> 範圍：三棒交卷點名的檔與周邊。檢查了而無發現的項目另列在本節末。

#### F-21｜維度 7／3｜**P2**｜（F-01 殘餘）TCS §4／§5.7 漏列 `BackupJobMigrationIT` 的前後快照相等斷言——V16～V18 落地後必紅，而 PKG-DB 被限定只准改版本清單

證據：
- `AgentConsole/backend/src/test/java/com/aisdlc/console/infrastructure/persistence/BackupJobMigrationIT.java:97`「`flyway(database, "14").migrate();`」；`:102`「`String before = snapshotOfExistingTables(jdbc);`」；`:106`「`flyway(database, null).migrate();`」（遷到最新版）；`:154`「`assertThat(snapshotOfExistingTables(jdbc)).as("既有各表的欄位與約束 V15 前後逐項相同（零變動）").isEqualTo(before);`」。
- `:82-90`：`snapshotOfExistingTables` 以 `information_schema.columns where table_schema = 'console' and table_name <> 'backup_jobs'` 與 `pg_constraint where connamespace = 'console'::regnamespace and conrelid::regclass::text <> 'console.backup_jobs'` 彙整「`console` 全部表（除 `backup_jobs`）」的欄位與約束。V16～V18 新增的 `research_*` 表因此會進 `after`、不在 `before`。
- 實測（本輪，拋棄式 PG18 庫，V1～V19 取自現稿 Δ14）：以該測試的欄位查詢，全表得 485 列；排除 `research_%` 表（＝V14 時的 `before`）得 199 列〔三審更正：這 199 列是 V19 庫，含視圖的 10 個欄位；P0 庫排除後與 V14 同為 189 列，見 I.5〕，兩者摘要不同；另有 393 列 `research_*` 約束會進 `after` 的約束段。`isEqualTo(before)` 必紅。
- 現稿對此測試的處置：`TCS:1800`（#13）只列 `BackupJobMigrationIT.java:167-168`（版本清單）；`TCS:1904`（§5.7 PKG-DB）「五個既有 IT 皆只改版本清單：`containsExactly` 的 1 至 15 改 1 至 18，方法名與其餘斷言不動」。

為何是問題：與一審 F-01 同型——凍結後 PKG-DB 一跑全套就紅，而依 §5.7 與 AT-960-18-5 的 GATE 核對不准動該斷言，只能回報主控走勘誤。SD-C 的重掃（`HARDPIN_SCAN.txt` 的 A～H）以版本字串、計數、集合鎖為正規式，沒有「跨版本前後快照相等」這一族；我對後端測試樹內全部 `information_schema`／`pg_*` 使用處逐一讀過，跨版本快照相等的只有這一處（其餘皆為單表斷言）。
修法：SD-C 在 §4 #13 的 `BackupJobMigrationIT` 子項補「`snapshotOfExistingTables`（`:82-90`）的欄位查詢加 `and table_name not like 'research\_%'`、約束查詢加 `and conrelid::regclass::text not like 'console.research\_%'`，使 V16 起的新表不入「既有表零變動」的比較（這是查詢條件的改動、不只是預期值，須在 §4 與 AT-960-18-5 的 GATE 說明列為與 #10 同型的例外）」；§5.7 PKG-DB 的括號改為「只改版本清單與 `snapshotOfExistingTables` 的排除條件」；RTM 與 SELF_CHECK 的硬釘清單補列；`HARDPIN_SCAN.txt` 增一組「前後快照相等」的正規式（`snapshotOf|isEqualTo\(before\)`）；SD-A 同步把計畫書 §4 鎖表 L4 的消費端（`PLAN:177`，D-64 已補列四個版本清單 IT 與 `OpenApiIT:247`）再加這一項。
該棒：**SD-C（主）＋SD-A（計畫書 L4 消費端一句）**。

#### F-22｜維度 3｜P4｜`floor_score` 仍可寫成 0，使「每維度地板」條件被架空（與 `threshold` 的範圍鎖不對稱）

證據：D-61 只鎖 `threshold`（`BETWEEN 50.00 AND 100.00`）；`floor_score` 沿用 `CHECK (floor_score BETWEEN 0 AND 100)`。探針 T05（`floor_score`＝0、`min_dimension_score`＝10、通過旗標為真、其餘自洽）→ ACCEPTED；T06（`floor_score`＝101）被擋。V18 的欄位註解（`ARCH` 的 `threshold` 一行）說「產品常數的範圍鎖…被寫成 0 會使 passed 恆真」，同一理由也適用 `floor_score`。
修法（建議）：`floor_score BETWEEN 40 AND 100`（或等於 60），並在 AT-960-1-E-7 加一列負控；若主控認為地板應可調到 0，則在 Δ14 註明「由 Bridge 寫入器保證」。該棒：SD-A（Δ14）＋SD-C（AT），不擋凍結。

#### F-23｜維度 2／6｜P4｜AT-960-8-1 的 Given 仍用被 D-62(3) 訂正的措辭

證據：`TCS:875`「有效清單為預設五個基底主機的 `check_research_url`（同一檢查函式 check_outbound_url 的獨立實例）」；D-62(3) 與 `PRD:480,912` 已改為「包裝函式：先呼叫 `check_outbound_url`，再加 https、埠 443、尾點、私網 IP 判準」。Then 欄的嚴格判準本身正確，只是括號字面過期。
修法：SD-C 把括號改為「包裝 `check_outbound_url`，D-62(3)」。該棒：SD-C。

#### F-24｜維度 3／2｜P4｜API-RP-20 的重試初始化模式，在非 FAILED 狀態下的回應未定義，而 AT-960-15-E-1 的第三次呼叫依賴它

證據：`API:246`「無 `generation`＝重試初始化：冪等——不覆寫已存在檔案、不重複配 `rpNo`、不重複建 FSM 鍵；僅 `flowStatus=FAILED` 且 `flowDetail` 以 `init_failed:` 起頭時可用」；`TCS:1221-1222`（AT-960-15-E-1）第三次重試初始化時 `flow_status` 已回 IDLE，預期「冪等：不覆寫已存在檔案、不重複建鍵…`research_gate_decisions` 與 `fsm_generation` 不再變」，但沒有釘 HTTP 回應碼；`API:275` 的回應欄對重試初始化只列「200 `{flow}`」。
修法：SD-A 在 API-RP-20 寫明非 FAILED 時回 200 無副作用（或 409 `fsm_state_conflict`），SD-C 在 AT-960-15-E-1 釘住該回應碼。該棒：SD-A（主）＋SD-C。

#### 已檢查而無發現的增量項目

- **D-60～D-64 落點一致**：上列 H.1.1；「換世代僅 ADMIN」在 `PRD:93,98,114,790,1049,1135,1267,1277`、`ADR003:34,104`、`ADR017:99`、`API:25,35-36,50,84,246,322`、`ARCH:109,139,141,221,267`、`PLAN:177`、`CUI:20`、`TCS:83,1389,1442-1445,1495-1498,1802` 皆同一語意，未見「OPERATOR 可換世代」的殘句。
- **403 分寫與現碼一致**：VIEWER 在通用 POST 規則（`SecurityConfig.java:97`「`.requestMatchers("/api/v1/**").hasAnyRole("OPERATOR", "ADMIN")`」）即被擋，reason 為 `ACCESS_DENIED`（`RbacIT.java:99-102` 的 `$.reason`＝`ACCESS_DENIED`）；OPERATOR 通過授權鏈後由服務層回 `research_write_forbidden`。`API:36` 註記同名 reason 在 Bridge 傳輸層另指寫入權杖缺或錯，屬既有慣例：SI P2b 的 `si_write_forbidden` 同時指「帳號不在 deciders」與「權杖缺或錯」（`API_Contract_SelfImproving_P2b.md:143`、`Architecture.md:995`），故不判缺陷。
- **API §0.2 的「先中者定案」順序**：401→403 `ACCESS_DENIED`→403 `research_write_forbidden`（服務層，先於任何 Bridge 呼叫）→503→422→404→409→502／504，與授權鏈（`AuditLoggingFilter` 在 JWT 與限流之後、授權之前，`AuditLoggingFilter.java:32-34`）及服務層入口的先後相容。
- **DDL 收緊與 SD-C 的 1-E-7／1-9／1-E-8 逐欄一致**：1-E-7 的二十五個組合，我逐一對照 V18 的 CHECK：成功組（一）（三）（六）（七）（十一）（十二）（二十二）、23514 組（二）（四）（五）（八）（九）（十）（十三）（十四）（十五）（十六）（十八）至（二十四）、23502 組（十七）、threshold 組（49.99、100.01、0 丟 23514；50.00、100.00 成功），與 DDL 行為相符（探針 R01～R17、T00～T04 為實證）；1-9 的部分唯一索引情境（QUEUED 後再插 RUNNING、RUNNING 後再插 QUEUED 或 RUNNING 被擋；終態列、BLOCKED_DB 列、另一研究專案的 RUNNING 成功；原 RUNNING 轉 SUCCEEDED 後可再插）與探針 C01～C04、CON01 相符；1-E-8 的八種 url／host 違規（含 host 為空字串）與 `research_fetches_host_check` 及探針 F02、F06 相符。
- **新 AT 的可測性**：13-8、12-E-5（引擎事實吻合，見 H.1.1）、15-8、15-9、15-E-1（除 F-24）、4-8、13-9、16-E-4、5-7 皆有 Given／When／Then／判定指令，期望值可由契約或現碼推出；`TCS:1801`（#14）的 OpenApiIT 新值我重算：24 條路徑（77＋24＝101）、26 個操作（4＋1＋1＋20＝26；89＋26＝115），與 AT-960-5-5 的 25 個研究 operationId 加 1 個串流操作相容。
- **SD-B 新 AT-970-7-6 與模板 §5.3**：AT-970-7-6 設 `SDD_ENABLE_AUTO_RECOVERY=0`，序列（用盡 3 次 → 恢復 → 再 FAIL → 再恢復 → PASS）與引擎行為逐步吻合；模板 §5.3 的轉移矩陣與 DDL 觸發器（`ARCH:693-694`）一致；`34` 個框架 AT 皆有 `Show-Result`（`scan_fwtcs.py`）。
- **Rule 9 與守衛面**：D-60 不改 `RETRY_LIMITS`、`_HAPPY_PATH`、`formal/`；恢復後再 FAIL 立即 ESCALATION，沒有「超上限仍重試」（禁令 4）；換世代是放棄舊鍵、不呼叫 `resume-from-escalation`（禁令 6）；本輪沒有新增 hook、鎖或守衛碼，也沒有新增 `os.replace`／`rename`／`move` 站點。

### H.3 機械檢核逐字輸出

1. **自寫掃描重跑**（`S\qa\*.py`，`python -I -X utf8`，皆 rc 0；輸出存 `S\qa\h_rerun_outputs.txt`）：`scan_ids.py`（FR 23、US 23、AC 171 唯一、NFR 主項 13；`HELM D 定義數: 53 min 12 max 64 缺: []`；`PRD 附錄 C 的 D 列: 63 缺（D-01~D-59）: [40]`〔D-40 在 PRD 以 C.6 呈現〕；「D 引用越界」的 60～64 是腳本內的舊上限常數，不是文件錯誤）、`scan_docsgate.py`（落檔面嚴格判準 0 命中；僅 `FW_TCS:72` 命中，屬 `AISDLC_SDD/AISDLC_SDD_v` 豁免樹，與 scratch-only 的 `EDITS:88`）、`scan_env.py`、`scan_enums.py`、`scan_anchors.py`＋`scan_anchors2.py`、`scan_cov.py`（`§1.2 列數 111  §1.3 列數 60`；排除表中屬 P0 起 FR 者仍只有 AC-R2P-18-2／18-3）、`scan_gwt.py`（`PRD AC 171 缺 G/W/T 或順序錯 []`；`TCS AT 區塊 210`；`判定指令缺漏或無法辨識 [] 0`）、`scan_dtext.py`（`HELM 53 PRD 63`；差異 3＝D-40〔C.6〕、D-42、D-53，皆附揭露句）、`scan_fwtcs.py`（`AT 定義數 34 唯一 34`、`負控(E) 9 正控 25`、`映射列數 34 AT 覆蓋 34`、`Show-Result 次數 34 涵蓋 AT 數 34`、`懸空 AC-R2P [] 懸空 FR-R2P []`、`D 引用越界 []`）、`scan_prelanded.py`（八個預先落檔檔皆 LF、無 BOM、docs 閘 0 命中；ADR-XPLAT-016 路徑宣稱 92 筆、ADR-XPLAT-017 路徑宣稱 28 筆，解析不到皆 0）。
2. `python -I -X utf8 S\sdc\_aux\selfcheck.py` → rc 0；87 行（86 行 PASS＋末行 JSON）：`{"AC": 24, "AT": 210, "AT_pos": 164, "AT_neg": 46, "US": 3, "V": 13, "P0_covered": "111/111", "out_of_scope": 60, "rtm_rows": 238, "problems": 0}`。
3. `python -I -X utf8 S\sdf\apply_framework_edits.py --edits S\sdf\FRAMEWORK_EDITS.md --root <R> --check` → rc 0；末行 `apply_framework_edits：檢查 48 個編修成功、0 個失敗（涉及 13 個檔）`。
4. `r2p_contract_check.py`：對聯集目錄（repo 既有 `agent/` 與 `docs_template/sdd/requirements/` 複本＋SD-B 現稿新檔，全新建立的 `S\qa\vd_union2`）→ rc 0，`r2p_contract_check: 9 個契約區塊、0 項問題`；`--selftest` → rc 0，`r2p_contract_check selftest: 29 個注入錯誤，漏網 0；1 個合法變體，誤判 0`；對 `sdf` 暫存樹（只含新檔）→ rc 1、5 項問題（與 `FRAMEWORK_VERIFY.md:95` 的前置說明一致，不是缺陷）。
5. **資料庫重跑**（本機 PG18 容器內全新拋棄式庫；V1～V15 取自 repo，V16～V19 以 `S\qa\extract_ddl2.py` 自現稿 Δ14 重抽，並與一審抽出版逐行比對：V16 +1 行〔部分唯一索引〕、V17 +3／−2、V18 +8／−3、V19 無差異）：19 個檔依序套用皆 rc 0；`research_*` 表 18 張；非內部觸發器 20 個。探針腳本 `ddl_tests.sql`、`ddl_tests2.sql`、`ddl_tests3.sql`、`ddl_tests4.sql` 皆 rc 0，逐字結果摘錄（`S\qa\h_ddl_probe_outputs.txt` 有全文）：
   - R01 `REJECTED [23514] … research_review_rounds_check6`；R06 `REJECTED [23514] … check7`；R14 `REJECTED [23514] … check8`；R15 `REJECTED [23514] … check7`；R17 `REJECTED [23514] … check8`（理由見 F-09 列）；CON01 `REJECTED [23505] duplicate key value violates unique constraint "ux_research_stage_runs_active"`；
   - T00 `ACCEPTED`（合法對照）、T01 `REJECTED [23514] … research_review_rounds_threshold_check`、T02 同、T03 `ACCEPTED`（threshold＝50.00）、T04 `REJECTED [23514]`、T05 `ACCEPTED`（F-22）、T06 `REJECTED [23514]`；C01 `ACCEPTED`、C02 `REJECTED [23505] … ux_research_stage_runs_active`、C03 `ACCEPTED`、C04 `ACCEPTED`；
   - F06 `REJECTED [23514] … research_fetches_host_check`；D08、D09 `REJECTED [23000]`、D10 `ACCEPTED`；S05、RN01～RN03 `ACCEPTED`（應用層保證，已明文）；R20、R21 `REJECTED [23000] research_review_rounds 為 append-only`；
   - G01 `ACCEPTED`（換世代單一交易：決定列 ABANDON_KEY／ABANDONED＋`fsm_project`、`fsm_generation` 同句更新）、G03 `REJECTED [23514]`（`fsm_generation`＝0）；G04 因表內無列而 `ACCEPTED`，屬空表假象，不計。
   - 用畢已 `DROP DATABASE`（rc 0；`pg_database` 剩餘 qa 庫 0）；容器暫存目錄內的複本檔因守衛擋下刪除指令而留在容器檔案系統（不在 repo、不在資料庫）。
6. **F-21 實測**：測試原 SQL 在 V19 庫得 485 列、排除 `research_%` 得 199 列、`research_*` 約束 393 列（見 F-21）。
7. **獨立硬釘掃描**（唯讀；Grep）：（a）前端 `components`、`tests`、`lib` 的 `toHaveLength|toHaveCount|.length).toBe` 對 8～10、18～25、77、84、89：落在 SD-C §4 之外的命中皆與本期無關（議題列數、監控區段、`stateKeys.test.ts:296` 的十張固定具名表、`lib/help/registry.test.ts:270` 的測試自有 19 條路由表等）；（b）後端測試樹的 `information_schema|pg_trigger|pg_class|pg_constraint|pg_indexes`：僅 `BackupJobMigrationIT.java:82-90,154` 是跨版本前後快照相等（F-21），其餘為單表斷言；（c）Bridge 測試的 `openapi|paths|routes`：`test_resources.py:606-617` 只比對 `ResourcesOut`／`RunStateOut` 的屬性，不釘路由總數；（d）框架側：`AISDLC_SDD_v0.30/tools/fsm_runtime/tests/test_arch_fitness.py:302-311` 的 count-drift 用合成樹、`test_subagent_contract.py:234` 只讀 `sdd-orchestrator`，根層 `tools/tests` 對 `agentconsole-ci.yml` 只有 `test_doc_loc_baseline_freshness_r60.py:5231` 的 ONBOARDING 表③ 錨點測試，不受 `paths` 編修影響。
8. 本報告自身的 docs 閘重掃：見 H.5 末行（最後一次編修後執行）。

### H.4 判定與計數（二審）

| 嚴重度 | 計數 | 發現 |
|---|---|---|
| P1 | 0 | — |
| P2 | 1 | F-21（SD-C 主；SD-A 補計畫書 L4 一句） |
| P3 | 0 | — |
| P4 | 3 | F-22（SD-A＋SD-C）、F-23（SD-C）、F-24（SD-A＋SD-C） |

一審 20 項：**落實 18**（F-02、F-03、F-04、F-05、F-06、F-07、F-08、F-10、F-11、F-12、F-13、F-14、F-15、F-16、F-17、F-18、F-19、F-20）、**部分落實 2**（F-01：殘餘＝F-21；F-09：`floor_score` 未鎖＝F-22）、**未落實 0**。一審 P2 四項：F-02、F-11、F-12 落實；F-01 部分落實。

**判定：FAIL**（P2＝1）。F-21 修畢（SD-C 補一列與 §5.7 一句）即可 PASS；F-22～F-24 不擋凍結，可隨 F-21 一併修或帶入實作期。

### H.5 誠實劃界（二審）

1. **增量審查不是完整 diff**：我沒有一審時各檔的完整複本（只有當時抽出的 DDL 與掃描輸出），所以 rc3 的變動是依主控點名的檔、D-60～D-64 的詞彙與座標逐處讀取與 grep 找出，不保證沒有未被這些詞彙觸及的改動；PRD 的 171 條 AC 本文、ADR-003 D2／D7／D11 以外、計畫書 §3～§8、框架工作流其餘章節、兩支 agent YAML，二審沒有重讀。
2. **引擎行為是讀碼推演，不是實跑**：13-8、12-E-5、AT-970-7-6 的預期值我以 `state_loader.py`、`fsm_runtime.py`、`transition_rules.py` 現碼逐步推演吻合，但沒有執行 FSM CLI（任務書禁寫入動詞），這幾個 AT 與 SD 自己標的一樣屬「未實跑」。
3. **資料庫只在 PG18 拋棄式庫、Windows 單機驗**；探針由我依 Δ14 與 D-61 設計，非窮盡；V19 只驗得套用成功與 CHECK／觸發器語法，P1 期的行為不在本輪範圍。
4. **硬釘掃描是正規式加人工讀取**：F-21 這一族是我讀完後端測試樹全部 `information_schema`／`pg_*` 用法才找到；其他可能的族（例如實作期才出現的建構子簽章變動使測試編譯失敗）在規格階段無法預見。
5. **一審更正**：一審 F-16 的證據句把 REGRESSED 的出口寫成「OPEN／FIXED」是我的轉述錯誤（見 H.1 的 F-16 列），結論（模板 §5.3 須補矩陣）仍成立且已落實。
6. **嚴重度是判斷**：F-21 與一審 F-01 同型，故判 P2；若主控認為單一測試的前後快照可在實作期以勘誤處理，可降為 P3，但這與一審對 F-01 的標準（凍結前必須收齊）不一致，建議維持 P2。
7. **時效**：基準＝三棒在本輪修訂後的現稿（PRD 的最後寫入在 10:11 前後）；審查期間若檔案再變動，以複審為準。

〈二審進度〉：H.1～H.5 已完成並定稿，已交卷。本報告自身重掃（`scan_report.py`、`check_tables.py`，最後一次編修後）：docs 閘嚴格判準、斜線對、磁碟絕對路徑、日曆承諾、雜湊字樣五項命中皆為 0；LF 行尾、無 BOM；全部 Markdown 表每列欄數與表頭一致。

## I. 三審

> 三審範圍（主控指令，範圍最小化）：二審 F-21～F-24 依 D-65 的修訂是否落實，加上 SD-C 順手對齊四處與 SD-A 三句敘述、D-65 範圍字樣一致性，並重跑拋棄式 PG 驗證 floor 探針。座標一律指向現稿；縮寫同 H 節。

### I.1 逐條落實表

| 項 | 二審嚴重度 | 三審狀態 | 座標與逐字證據 |
|---|---|---|---|
| F-21 §4 #13 子項 | **P2** | **落實** | `TCS:1801`：「另（SCG-0 二審 F-21；D-65(1)）同目錄 `BackupJobMigrationIT.java:82-90`（`snapshotOfExistingTables` 的欄位查詢與約束查詢）與其呼叫點 `:97`（遷到 14）、`:102`（取 `before`）、`:106`（遷到最新版）、`:154`（前後快照相等斷言）」；改後值「`snapshotOfExistingTables` 的欄位查詢加 `and table_name not like 'research\_%'`、約束查詢加 `and conrelid::regclass::text not like 'console.research\_%'`（LIKE 以反斜線跳脫底線；寫進 Java 字串字面值時反斜線要寫成 `\\`）…`:97`、`:102`、`:106` 的呼叫、`:154` 的 `isEqualTo(before)` 與其說明字串、兩個查詢的其餘字樣不動」；理由欄「這是查詢條件的改動、不只是預期值，與第 10 列同為「不只改預期值」的例外（既有 `console` 表在 V16 至 V18 前後仍須逐項零變動，語意不減弱）；V19（P1）新增的視圖 `console.v_research_healing_attempts` 不以 `research_` 起頭，P1 鍵落 V19 時須再擴此排除條件」。我的實測（I.3 第 5 項）證實排除條件在 P0 足以使前後快照相等，且 V19 視圖的提醒屬實。 |
| F-21 §4 前言例外 | — | 落實 | `TCS:1778`：「**例外（不只改預期值；各列自寫 hunk 範圍與理由，GATE 核對時逐列放行，其餘 hunk 一律照共同規則）**：第 10 列…與第 13 列的 `BackupJobMigrationIT` 子項（`snapshotOfExistingTables` 的兩個查詢條件，AT-960-1-E-1 核對；SCG-0 二審 F-21、D-65(1)）」；`TCS:1984` 的收尾核對條件同步列此例外。 |
| F-21 §5.7 PKG-DB | — | 落實 | `TCS:1905`：「五個既有 IT 只改版本清單與 `snapshotOfExistingTables` 的排除條件：`containsExactly` 的 1 至 15 改 1 至 18、`BackupJobMigrationIT` 的兩個快照查詢各加排除 `research_` 起頭之表與其約束的條件，方法名與其餘斷言不動；§4 #13；D-65(1)」。 |
| F-21 D1 交付物 | — | 落實 | `TCS:60`：「`BackupJobMigrationIT` 另改 `snapshotOfExistingTables` 的排除條件，§4 #13、D-65(1)」。 |
| F-21 AT-960-1-E-1 | — | 落實 | `TCS:1684-1688`：標題「五個版本清單，加 BackupJobMigrationIT 的前後快照排除 research 表」；Given 含 `:82-90`、`:97`、`:102`、`:106`、`:154`；When 逐字列出兩個查詢條件與 Java 字串的 `\\`；Then「`:154` 仍為 `isEqualTo(before)`…研究表與其約束不入比較、既有表零變動的語意不減弱；`git diff`…另動上述兩個查詢條件（被刪的斷言行為 0…）」。 |
| F-21 RTM | — | 落實 | `RTM:46`（AT-960-1-E-1 列說明「五個版本清單，加 BackupJobMigrationIT 的前後快照排除 research 表」）；RTM 列數仍 238（`selfcheck.py`）。 |
| F-21 HARDPIN_SCAN | — | 落實 | `sdc\_aux\HARDPIN_SCAN.txt:331-431`：I 組（`snapshotOf\|isEqualTo\(before\)`，9 行 6 檔）、I′ 組（換名旁證形態，14 行 10 檔）、J 組（`information_schema`／`pg_*`／`regnamespace` 的位置，41 行 6 檔）、K 組（`migrationsExecuted`、`info()`、`pending()`、`db/migration`，17 行 5 檔）。我對 J 組逐行核對：跨版本快照相等只有 `BackupJobMigrationIT.java:85-87,154`，其餘皆單表斷言；`SettingsWriteApiIT.java:404-408` 還以 `containsExactlyInAnyOrder` 釘住 `audit_log` 恰十欄，正好佐證 D-62(1)「不新增欄位、不改 V6」。 |
| F-21 計畫書 L4 | — | 落實 | `PLAN:177`「**另一項前後快照相等斷言**（QA 二審 F-21，D-65）：`…BackupJobMigrationIT.java:97,102,106,154`…修法是**查詢條件**的改動（查詢須排除 `research_%` 表與其約束，LIKE 的底線要跳脫），不只是預期值，須與 PKG-DB 同包同步並在 TCS 列為「不只改預期值」的例外」；`PLAN:44` 的 P0 DB 列同句。 |
| F-22 DDL | P4 | **落實** | `ARCH:612`（Δ14 K.3）：「`floor_score INTEGER NOT NULL DEFAULT 60 CHECK (floor_score BETWEEN 50 AND 100)`…D-14／D-42／D-65：任一維度不低於地板（初值 60、未校準）；範圍鎖與 threshold 對稱，地板被寫成 0 會架空 D-14」。與二審抽出版逐行比對：四個檔只有這一行不同。 |
| F-22 驗收段與 PRD | — | 落實 | `ARCH:855`：「**D-65 地板鎖**：`research_review_rounds.floor_score` 低於 50 或高於 100 被擋（與 `threshold` 的範圍鎖對稱…初值 60 與邊界 50、100 通過）」；`PRD:1249`（§9.2）：「`floor_score INTEGER`（預設 60，範圍 50～100；D-65）」；`TCS:1858`（§5.1 常數表）「限 50 至 100（D-65(2)…）」；`RTM:52`。 |
| F-22 AT-960-1-E-7（二十六） | — | 落實 | `TCS:1325-1326`：「（二十六）floor_score 為 0、49 與 101 各一列（0 的列 min_dimension_score 為 10、通過旗標為真…49 的列 min_dimension_score 為 60、通過旗標為真…101 的列通過旗標為假…）；floor_score 為 50 與 100 各一列（50 的列 min_dimension_score 為 60、100 的列 min_dimension_score 為 100…）」，Then「0、49、101 三列丟 `23514`…50 與 100 兩列成功」。五列的期望值我逐列對 DDL：0 與 49 在舊 DDL 會被接受（通過旗標的 CHECK 只比較最低維度與地板）、現被範圍鎖擋；50 與 100 通過（最低維度 60 與 100 各不低於地板）；101 的列只有範圍鎖一個違規。資料庫實測五列結果相同（I.3 第 5 項 FL01～FL05）。 |
| F-23 | P4 | **落實** | `TCS:876`：「被測函式為 `check_research_url`（新建於 `app/research/fetch/allowlist.py`；D-62(3)），它包裝既有的 `check_outbound_url`（`app/security.py:275-303`）：先呼叫既有函式…再加 https 限定、埠 443 限定、尾點拒絕與解析後私網 IP 拒絕；`check_outbound_url` 本身不修改（它接受 http、任意埠與尾點）」；`TCS:878` 加差異對照：「以同一份清單直接呼叫 `check_outbound_url`，`http://export.arxiv.org/x`、`https://export.arxiv.org:8443/`、`https://export.arxiv.org./` 三者回放行，`check_research_url` 對這三者回拒絕，其餘形態兩者的放行與拒絕一致」。我對照 `security.py:283-303`：scheme 只擋非 http／https、不查埠、host 先 `lower().rstrip(".")`、userinfo 與 parser 不一致才拒——三個「放行」與其餘八個形態的「一致」判斷（清單共十一個 URL）皆與現碼相符。 |
| F-24 契約 | P4 | **落實** | `API:246`（API-RP-20）：「只在 `flowStatus=FAILED` 且 `flowDetail` 以 `init_failed:` 起頭時可呼叫，其餘狀態一律 409 `stage_conflict`（`details.flowStatus`／`flowDetail`）、零寫入（無檔案寫入、無 FSM 動作、無 DB 變更；D-65：回應碼要寫定，不留給實作期各寫各的）」；`API:275`（Bridge 端點表）「重試初始化：409 `stage_conflict`（`flow_status` 非 FAILED，或 `flow_detail` 不以 `init_failed:` 起頭；`details.flowStatus`／`flowDetail`；零寫入，D-65）」；`ARCH:266` 同。 |
| F-24 PRD | — | 落實 | `PRD:460`（FR-R2P-03 邊界條件）：「只在 `flow_status=FAILED` 且 `flow_detail` 以 `init_failed:` 起頭時可呼叫，其餘狀態 409 `stage_conflict`…零寫入；D-65」；`PRD:469`（AC-R2P-03-5 第二個 Given）：「研究專案的 `flow_status` 不是 FAILED，或 `flow_detail` 不以 `init_failed:` 起頭（例：重試成功後已回 IDLE） When 呼叫 `POST …/reinit`（不帶 `generation`） Then 409 `stage_conflict`…零寫入（無檔案寫入、無 FSM 動作、無 DB 變更；D-65）」。 |
| F-24 AT | — | 落實 | `TCS:775-779`（AT-960-3-4）：第二次 reinit（`flow_status` 已為 IDLE）回 409 `stage_conflict`，`details.flowStatus` 為 `IDLE`，零寫入；三個對照專案（IDLE、ESCALATED、FAILED 而 `flow_detail` 為 `stage_failed:x`）各回 409 且 `details` 逐值等於當下欄位；`TCS:1220-1223`（AT-960-15-E-1）：第三次（補建成功後）回 409 `stage_conflict`、`details.flowStatus` 為 `IDLE`、零寫入（不覆寫檔案、FSM 子行程記錄 0 筆、決定列與事件帳與 `research_projects` 皆不變）；`TCS:90`（W-R12）、`TCS:126`、`TCS:414`、`RTM:66`、`RTM:189` 同步。二審 F-24 指出的「第三次呼叫的回應碼未釘」已釘為 409。 |
| 順手對齊 SD-C | — | 落實 | AT-960-15-9（`TCS:1443-1446`）標題與 Then：「OPERATOR 403 research_write_forbidden（服務層）、VIEWER 403 ACCESS_DENIED（既有授權鏈）」「不帶 `generation` 的重試初始化 OPERATOR 回 200、VIEWER 回 403 `ACCESS_DENIED`」；§4 #15（`TCS:1803`）「OPERATOR 回 403 `research_write_forbidden`、VIEWER 由既有授權鏈擋而回 403 `ACCESS_DENIED`，兩者各釘一個斷言」；⚖31（`TCS:1976`）與 ⚖32（`TCS:1977`）同語意。與 `SecurityConfig.java:97`、`RbacIT.java:99-102` 一致（二審已核）。 |
| SD-A 三句敘述 | — | 落實 | `PRD:10`「主控裁決 D-12～D-65…D-65 依二審校準」；`PRD:20`「SCG-0 一審 FAIL 已依 D-60～D-64 修訂、二審依 D-65 修訂；待三審與主控凍結」；`PLAN:312`「二審 FAIL（P2 1）已依 D-65 修訂；待三審；主控裁決 D-12～D-65」。 |
| 範圍字樣一致性 | — | 落實 | 七檔首行皆「D-01～D-65」（`ADR017:1`、`PRD:1`、`CUI:1`、`PLAN:1`、`ARCH:1`、`API:1`、`ADR003:1`），次行或本文為「D-12～D-65」（`PRD:10`、`PLAN:5,15`、`API:5`、`ADR003:9`、`TCS:1942`）；殘留的「D-60～D-64」只在變更紀錄與歷史句（`PRD:20,24,1465`、`API:16`、`PLAN:312`），描述當時範圍，不是過期。`HELM_DECISIONS.md:65`（D-65）與 `PRD:1700`（附錄 C.7）逐字相同（`scan_dtext.py`：HELM 54 列、PRD 64 列，差異仍只有 D-40〔C.6〕、D-42、D-53 三項既有揭露）。 |

### I.2 新發現

#### F-25｜維度 3／2｜P3｜D-59(1) 與 D-61 兩條 CHECK 合起來，使「解析不出 host 的被拒外呼」無法入庫，而 AT-960-8-1 要求每個被拒形態都留一列

證據：
- DDL：`ARCH:511`「`CHECK (fetch_method = 'WEB_SEARCH' OR (url IS NOT NULL AND host IS NOT NULL))`」（D-59(1)）與 `ARCH:513`「`CHECK (host IS NULL OR host <> '')`…DENIED 列也一樣」（D-61）。非 `WEB_SEARCH` 的列 host 必須非 NULL 且非空字串。
- AT：`TCS:877` 的檢查清單含 `file:///etc/passwd`；`TCS:878`「其餘一律拒絕並各產生一筆 `outcome` 為 `DENIED_ALLOWLIST` 的 `research_fetches` 列（含 host、url、layer）」。`file:///etc/passwd` 的 `check_outbound_url` 回傳 host 為空字串（`security.py:295`：`return False, parts.hostname or "", "scheme_not_allowed"`）。
- 實測（本輪拋棄式庫，V1～V19）：H01 host 為空字串 → `REJECTED [23514] … research_fetches_host_check`；H02 host 為 NULL → `REJECTED [23514] … research_fetches_check`；H03 host 為占位字串 → ACCEPTED；H04 可解析 host 的被拒外呼 → ACCEPTED。
- 現稿沒有任何一處說明無 host 的被拒外呼（`file://`、空字串、畸形 URL）如何記錄；PRD AC-R2P-04-2 只寫「allowlist 外 URL…一律被拒並留一筆…抓取紀錄」。

為何是問題：實作者照 AT 為 `file:///etc/passwd` 寫列會撞 CHECK（寫空字串或 NULL 皆被拒），只能自行發明占位 host；各寫各的會讓稽核資料不一致。這個組合來自 D-61 採納我一審 F-17 的「host 非空」建議，與 D-59(1) 的合成效果，我在二審核對 1-E-8 時沒有一併核對 AT-960-8-1 的 `file://` 形態。不判 P2 的理由：AT 沒有釘死該列的 host 值，任何非空占位都能讓 AT 通過，不會「凍結後必紅」。
修法（建議，不擋凍結）：SD-A 在 PRD §5.1.3（抓取入庫對映）與 ADR-003 D7 寫明「URL 解析不出 host（無 scheme 對應的 host、空字串、畸形）時，`research_fetches` 列的 host 取固定占位字串（建議 `(unparsed)`）、url 取原字串前 500 字元」或改為「不入庫，只記 `research.denied` 事件」；SD-C 在 AT-960-8-1 的 Then 對 `file:///etc/passwd` 寫明該列 host 的期望值。該棒：SD-A（主）＋SD-C。

### I.3 機械檢核逐字輸出

1. 自寫掃描重跑（`python -I -X utf8`，皆 rc 0；輸出存 `S\qa\i_rerun_outputs.txt`）：`scan_ids.py`（`HELM D 定義數: 54 min 12 max 65 缺: []`；`PRD 附錄 C 的 D 列: 64 缺（D-01~D-59）: [40]`）、`scan_docsgate.py`（落檔面嚴格判準 0 命中；僅框架豁免樹的 `FW_TCS:72` 與 scratch-only 的 `EDITS:88`）、`scan_env.py`、`scan_enums.py`、`scan_anchors2.py`、`scan_cov.py`、`scan_gwt.py`（`PRD AC 171 缺 G/W/T 或順序錯 []`；`TCS AT 區塊 210`；`判定指令缺漏或無法辨識 [] 0`）、`scan_dtext.py`（`HELM 54 PRD 64`；差異 3＝D-40、D-42、D-53，D-65 無差異）、`scan_fwtcs.py`（34 AT、Show-Result 34）、`scan_prelanded.py`（八檔 LF、無 BOM、docs 閘 0）。
2. `python -I -X utf8 S\sdc\_aux\selfcheck.py` → rc 0；103 行（102 行 PASS＋末行 JSON）：`{"AC": 24, "AT": 210, "AT_pos": 164, "AT_neg": 46, "US": 3, "V": 13, "P0_covered": "111/111", "out_of_scope": 60, "rtm_rows": 238, "problems": 0}`。
3. `python -I -X utf8 S\sdf\apply_framework_edits.py --edits S\sdf\FRAMEWORK_EDITS.md --root <R> --check` → rc 0；`apply_framework_edits：檢查 48 個編修成功、0 個失敗（涉及 13 個檔）`（框架側本輪無變動，重跑確認）。
4. `S\qa\extract_ddl3.py` → rc 0；自現稿 Δ14 重抽 V16～V19 與二審版逐行比對：V16、V17、V19 無差異，V18 `+1 −1`（僅 `floor_score` 一行：`CHECK (floor_score BETWEEN 0 AND 100)` 改為 `CHECK (floor_score BETWEEN 50 AND 100)`）。
5. **資料庫重跑**（本機 PG18 容器內三個全新拋棄式庫：V1～V14、V1～V18〔P0〕、V1～V19；19 個檔依序套用皆 rc 0；P0 庫 13 張、V19 庫 18 張 `research_*` 表，觸發器 15 與 20 個）。探針腳本 `ddl_tests5.sql`（新）與一、二審的 `ddl_tests.sql`、`ddl_tests2.sql`、`ddl_tests3.sql` 皆 rc 0，逐字結果摘錄（全文在 `S\qa\i_ddl_probe_outputs.txt`）：
   - floor：FL00 預設 floor（60）`ACCEPTED`；FL01 floor＝0、最低維度 10 `REJECTED [23514] … research_review_rounds_floor_score_check`；FL02 floor＝49 同；FL03 floor＝50（最低維度 60）`ACCEPTED`；FL04 floor＝100（最低維度 100）`ACCEPTED`；FL05 floor＝101（未通過列）`REJECTED [23514] … research_review_rounds_floor_score_check`；FL06 floor＝0（未通過列）同；FL07 threshold＝49.99 `REJECTED [23514] … research_review_rounds_threshold_check`。一審探針 T05（floor＝0、最低維度 10）二審為 ACCEPTED，現為 `REJECTED [23514] … floor_score_check`。
   - 回歸：R01、R06、R14、R15 仍 REJECTED（`…_check6`、`…_check7`、`…_check8`、`…_check7`）；CON01 `REJECTED [23505] … ux_research_stage_runs_active`；F06 `REJECTED [23514] … research_fetches_host_check`；T01～T04、C01～C04、D08～D10、S05、RN01～RN03、R20、R21 與二審結果相同。
   - F-25：H01、H02、H03、H04 見上。
   - **F-21 前後快照實測**（以測試原 SQL，連線用預設 search_path，與 JDBC 相同）：V14 庫欄位快照 189 列、約束快照 141 列；P0 庫（V18）原查詢欄位 400 列、約束 450 列，**與 V14 不相等**（`isEqualTo(before)` 必紅，一審 F-21 成立）；加上 D-65 的排除條件後，P0 庫欄位 189 列、約束 141 列，**與 V14 的摘要逐值相等**；V19 庫排除後欄位為 199 列（多出的 10 列＝視圖 `v_research_healing_attempts` 的欄位，與 `TCS:1801` 的 P1 提醒一致）、約束仍相等。
   - 用畢三庫皆 `DROP DATABASE`（rc 0；剩餘 qa 庫 0）。
6. 讀碼對照：`security.py:275-303`（F-23 的差異對照）、`SecurityConfig.java:97` 與 `RbacIT.java:99-102`（順手對齊四處）、`BackupJobMigrationIT.java:82-90,97,102,106,154`、`SettingsWriteApiIT.java:404-408`。
7. 本報告自身的 docs 閘重掃：見 I.5 末行（最後一次編修後執行）。

### I.4 判定與計數（三審）

| 嚴重度 | 計數 | 發現 |
|---|---|---|
| P1 | 0 | — |
| P2 | 0 | — |
| P3 | 1 | F-25（SD-A 主＋SD-C；不擋凍結） |
| P4 | 0 | — |

二審 F-21～F-24：**落實 4、部分落實 0、未落實 0**；順手對齊四處與三句敘述、D-65 範圍字樣皆落實。至此一審 F-01～F-20 與二審 F-21～F-24 共 24 項全部關閉（一審部分落實的 F-01、F-09 其殘餘 F-21、F-22 已落實）。

**判定：PASS**（P1＝0 且 P2＝0）。F-25 為 P3，建議在凍結前以一句話補上（SD-A 一句、SD-C 一句），但不阻擋凍結；若主控選擇帶入實作期，須在開發棒任務書的 PKG-BR-B 段寫明占位 host 的決定。

### I.5 誠實劃界（三審）

1. **範圍最小化**：只核 D-65 觸及的各處與主控點名的對齊項；PRD 本文其餘章節、ADR-003 其餘決策、框架側文件（本輪沒有變動）、AT 其餘部分未重讀，沿用一、二審的抽樣深度。
2. **Java 測試未實跑**：F-21 的排除條件效果是以測試原 SQL 在拋棄式庫模擬（預設 search_path，與 JDBC 連線相同），沒有跑 gradle（規格階段沒有生產碼，repo 唯讀）；`LIKE` 跳脫在 Java 字串內寫成 `\\` 的處理，我只核對了文字，沒有編譯。
3. **二審數字更正**：二審 H.3 第 6 項與 F-21 證據寫「排除 research_% 後 199 列（＝V14 時的 before）」不精確——那是 V19 庫，多含視圖的 10 個欄位；P0（V18）庫排除後與 V14 同為 189 列。結論（原查詢必紅、排除後相等）不變。
4. **F-25 的來源**：由我讀 AT-960-8-1 對照 DDL 時發現，不是 D-65 引入；D-61 的 host 非空鎖出自我一審 F-17 的建議，這是我在二審漏核的組合效果。
5. **容器殘留**：二審與三審的 SQL 複本在容器檔案系統的暫存目錄（因守衛擋下刪除指令而未清）；不在 repo、不在任何資料庫，三個庫已全數丟棄。
6. **引擎與 FSM**：三審沒有動到 FSM 相關文字，D-60 的讀碼推演沿用二審。

〈三審進度〉：B 節（B.1 三審、B.2 二審、B.3 一審）與 I.1～I.5 皆已完成並定稿，純文字交卷為本輪最後一步；本報告自身重掃結果（最後一次編修後，工具 scan_report 與 check_tables，rc 皆 0）：docs 閘門啟發式 strict 0、pair 0、abs 0、cal 0、sha 0，檔案為 LF 且無 BOM，Markdown 表格共 8 張、欄數不符 0 張。
