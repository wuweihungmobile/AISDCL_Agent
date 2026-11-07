# SCG0-REVIEW-ResearchToPRD-P2（2026-11-07；鍵 `agentconsole-research-to-prd-p2` 預備；TCS-ResearchToPRD-P2 覆蓋審）

> 主控落檔說明：本檔由獨立 QA（Sonnet）在 scratchpad 寫成，對 SD 棒的 TCS-ResearchToPRD-P2 做輕量 SCG-0 增量審（覆蓋、
> 可執行性、硬釘重掃、常數邊界、裁決一致、V21 DDL 草案）。一審 FAIL（P2 6：D-142 兩項未回填、第七項對帳連動漏列、
> `GateRegisterDialog` 無 AT、掃描自我命中…）→ SD 續棒 → 二審 FAIL（P2 1：§4.4 E1 事件鍵）→ SD 第三輪四處 → **三審 PASS**
> （P1～P4 全 0）。**最終判定以文末〈三審〉為準**。主控裁決 D-142／D-144／D-145 為 oracle。英文計數字樣（passed／skipped／
> tests）一律改為中文以符基線數字守門；數字本身未改。

# TCS-ResearchToPRD-P2 覆蓋審（輕量 SCG-0 增量審；QA 獨立、唯讀）

審查對象：`S\sd\p2\TCS-ResearchToPRD-P2-20261107.md`（2406 行）、`RTM-ResearchToPRD-P2-20261107.md`、`V21_DDL.md`、`_aux\`。S＝scratchpad `r2p1`。
工作樹 HEAD＝`8380142a`（SD 寫稿時為 `a339c66f`；以下座標皆對現檔行號核實）。自寫解析腳本在 `S\qa\p2\`（parse.py、cov.py、show.py）；未執行 SD 的 selfcheck.py（它會覆寫 SELF_CHECK.md，違唯讀）。

## A 判定與計數
**判定：FAIL**（P1 0、P2 6、P3 6、P4 1）。P2 為「D-142 未回填 2 項」＋「既有測試硬釘漏列」＋「UI 半條無 AT」＋「一支 AT 掃描範圍自我命中」。無 P1：PRD 的 P2 AC 全數有 AT。

## B 發現表

| F | 嚴重度 | TCS 座標 | 問題 | 修法（指名 SD 棒） |
|---|--------|----------|------|------------------|
| F-01 | P2 | W-R2P9 :89；AT-962-8-4 :926；AT-962-18-E-5 :1071；§7 ⚖P2-9 :2352；AC-962-8 :159 | 條文仍是「漂移只記錄與告警、不阻擋」，與 D-142（⚖P2-9 改判）衝突。D-142：`:tag` 與 `:gates` 前置漂移＝422 `digest_mismatch`＋`details.drift[]{path,expected_sha256,actual_sha256}`，零寫入、零 FSM 呼叫；`:healing-sync` 仍只記錄加告警。TCS 缺：18-E-5 改 422；`:gates` 同型負控；console-api 透傳 422 `digest_mismatch` 的 AT（AT-962-19-5 只有 tag_exists／delivery_step_failed）；漂移檢查在檢查序中的位置（3-E-1、26-E-1 只寫「權杖→DB→專案→本文→前置」）。`digest_mismatch` 已在 P0 的 22 個（`ResearchReasonsTest.java:51`），四方鎖仍 37，不必增 reason。 | SD 修：W-R2P9、AT-962-8-4、18-E-5（改 422）、新增 `:gates` 負控 AT（Bridge 與 console-api 各一，RTM 與檔頭計數同步）、AC-962-8 Then、⚖P2-9 列改「採納 D-142」 |
| F-02 | P2 | §4 缺列；AT-962-23-4 :1139；⚖P2-15 :2358；§4.5 :2236 | 對帳呼叫點鎖**存在**：`test_research_reconcile.py:331 test_AT_960_21_4_p0_has_only_the_gate_0_call_site_for_reconcile`，:339 斷言 `sorted(檔名)==["app/routers/research.py"]*3`。P2 新增 `reconcile_at_delivery` 呼叫點後必紅（個數 3→4，若呼叫點在 `research_deliver.py` 連檔名集合也變）。SD 宣稱「不存在」（:1139、:2358）是錯的。 | SD 修：§4.2 補一列（檔:行、現值 3、改後值、呼叫點落在哪個檔、持有包 BR-P2）；AT-962-23-4 刪「不倚賴既有鎖」改為更新該鎖並保留自帶次數斷言；⚖P2-15 與 §4.5 末句更正 |
| F-03 | P2 | §4 缺列；§4 第 41 列 :2220；§5.7 INT-P2 :2302；AT-962-23-7 :1957 | 第七項 `delivery` 會轉紅、但 §4 未列的既有測試：(a) `frontend/tests/e2e/research-docker.stack.spec.ts:339-346`（`checks.map(name).sort()` `toEqual` 六名；第 41 列寫「不改既有 spec」，且 INT-P2 允許集合不含此檔，必紅於 Docker E2E）；(b) `frontend/lib/domain/research.test.ts:710-714`（`Object.keys(RECONCILE_CHECK_LABEL)` `toEqual(SIX_CHECKS)`、`Set size 6`）與 `research.ts:517-525` 標籤表（AT-962-23-7 要「漂移橫幅顯示 delivery 項」，沒說是否加標籤）；(c) `engine-bridge/tests/test_research_reconcile.py:99-101`（`{id: present}` 六鍵整張字典 `==`）。第 20 列只列 `:92,:96,:490`。 | SD 修：§4 補三列（只改預期值）；第 41 列改為「例外：只改 `:339-346` 的期望名單」並把該檔列入 INT-P2 允許集合；23-7 明寫是否新增 `delivery` 標籤 |
| F-04 | P2 | §4 第 32 列 :2211；AT-962-24-6 :1967 | `frontend/lib/domain/research.test.ts:958-959` `expect(values).toHaveLength(35)`（`RESEARCH_REASONS`）漏列；35→37 必紅。第 32 列只寫 `research.ts:749/793`。 | SD 修：第 32 列加 `research.test.ts:958-959`，24-6 Then 加「長度 37」 |
| F-05 | P2 | AC-R2P-15-6 的 UI 半；§1.2 :258；AC-962-15 的 AT-962-15-5 :1837 | PRD 15-6「ADMIN 於回歸驗收欄登錄 SCG-4…確認框聲明審查者未參與規格與實作」是 UI 行為；§5.7 把 `GateRegisterDialog.tsx` 派給 FE-P2A，但 vitest 沒有任何 AT 測它（Grep `GateRegisterDialog` 只在 AT-962-15-5 當停用對象；`reviewerIndependent|獨立|登錄` 的 vitest AT 為 0）。後端 AT 3-x、4-x 守不住對話框（聲明勾選才可送、FAIL 理由必填、RELEASE_READY 只有 FAIL、非 ADMIN 停用、結果與 ESCALATED 呈現、錯誤 reason 文案）。 | SD 修：新增 vitest `GateRegisterDialog.test.tsx` 的 AT（含至少 3 個負控：未勾獨立聲明、FAIL 無理由、非 ADMIN；理由 500／501 邊界），掛 AC-962-4 或新增 AC 並同步 §1.2、§1.5、檔頭計數、RTM |
| F-06 | P2 | AT-962-13-2 :1722 | Then 要求對 `components/domain/research/**` 「全檔」零命中 `/dangerouslySetInnerHTML/` 等。現檔註解已命中：`MermaidBlock.tsx:12`、`RouteActionList.tsx:5`、`StudioPanel.tsx:17`，測試檔 `EvidenceTimeline.test.tsx:154-158,216-241` 亦含；新增 `TerminalPane.test.tsx` 自己的正規式字面也會自我命中（P0 R-3 型）。照寫實作必紅或被迫改掃描範圍。現有先例 AT_960_10_4 用 `renderViolations`（排除測試檔、註解）。 | SD 修：13-2 明定「僅非測試原始碼、剝註解後掃描；正規式以字串拼接組成」，或沿 `EvidenceTimeline.test.tsx` 的掃描函式 |
| F-07 | P3 | AT-962-28-3 :1182 | Given「`CLAUDE_BIN` 指向 mock」：repo 內無此環境變數（Grep `AgentConsole`、`AutoClaude/autoclaude` 零命中）。現行機制是 `tests/conftest.py:236-244` 的 `run_body` ＋ config `claude.command`，劇本失敗用 `MOCK_CLAUDE_FAIL_REGEX`（`mock_claude.py:19`）。 | SD 修：改寫為現有載具 |
| F-08 | P3 | AT-962-3-E-5 :781 | Then「503 `db_blocked` 或 200 帶補寫標示」二擇一，不可機械判定。 | SD 修：先讀 P0 `DurableWriter` 現行契約，寫成單一值 |
| F-09 | P3 | AT-962-20-2 :1081、18-2 :1011、11-3 :1632、13-6 :1742、9-2 :1329 | 常數缺界內／界外對：PR 內文 4000（只有「超過時截斷」）、`detail` 2000、≤500ms（只有界內 499，無超界會失敗的對照）、`maxRetries`（只有 3→5，無 attempt＝max-1／max／max+1）。其餘（semver 64／65、標題 59／60／61、excerpt 299／300／301、2 MiB、evidence_url 500／501、snapshot 63／64／65、message 200／201、reason 500／501、AC 數 1／250）齊備。 | SD 修：補邊界案例（可併入既有 AT 的子情境） |
| F-10 | P3 | §4 第 26 列 :2200；AT-962-18-4 :1024 | `research.delivery` 不在 `db.py:67-87 EVENT_PAYLOAD_KEYS`（`append_event` :349-357 對未登記型別與鍵集合 fail-loud）。TCS 未列此登記，也沒規定必填／可選（`EVENT_OPTIONAL_KEYS` :89）：18-4 釘成功事件五鍵，`FAILED` 事件（20-7、W-R2P18）無 commitSha。既有 `test_research_events.py:195,:282` 以登記表做等式。 | SD 修：第 26 列加登記；新增一個 AT 釘 SUCCESS 與 FAILED 兩種 payload 鍵集合 |
| F-11 | P3 | AT-962-28-5 :2065 | 「Docker 全棧或本機模式（標明）」「走完起草與 Gate 0」：Gate 0 需真人點擊、研究劇本與內環劇本載具未指定；對應出口 (c) 的證據面不確定。 | SD 修：指定載具（建議本機模式＋夾具，標明）與 Gate 0 的代驗手法 |
| F-12 | P3 | AT-962-28-8 :2075；18-x | `:tag` 的容器模式前置（`route_unsupported_in_deployment`／`repo_writable`）只有 Docker E2E 一個 AT，Bridge 與 console-api 層無 hermetic AT（PR 側有 20-5）。 | SD 修：補 18-E-6 與 19 的透傳案例 |
| F-13 | P4 | §7 :2344-2362 | 12 項「待裁決」狀態仍為待裁決（D-142 已裁，SD 待回填）；AT-962-15-3 實測 AC-R2P-19-7 卻未在標題引用；AT-962-7-3 「Python 端記錄值」未說記在哪；`SecurityConfig.java` 規則實為 :103-111（TCS 寫 105-109）。 | SD 順手修 |

## C 覆蓋對照
PRD P2 核心 23 條（15-1～15-6、16-1～16-5、17-1～17-4、18-2、18-3、20-1～20-6）加增量 14 條（01-5、02-4、02-5、02-7、02-8、02-10、19-1、19-4、19-5、19-6、21-2、21-5、23-1、23-4）＝**37／37 各至少一個 AT**。我以 §3 各 AT 標題列抽出的 PRD 引用重建集合，與 §1.2 全表逐條集合相等（差集空）；`AC-962-1～30` 各有 AT（每 AC 正控 3～9、負控 2～5）。PRD 現查 FR-15=6、16=5、17=4、20=6、18 的 18-2／18-3，與 TCS 一致。§1.3 四項劃界皆附 WHY（無 P3）。子條款缺口：AC-R2P-15-6 UI 半（F-05）。

## D 抽查 AT（約 110 個實讀，每個 AC-962 至少一個；負控超過 40 個）
讀過：1-6/7/E-1～E-3、2-1～2-6、2-E-1/2、3-1～3-9＋E-1～E-5、4-1～4-6＋E-1～E-4、5-1～5-7＋E-1/2、6-1～6-8＋E-1～E-3、7-1～7-5＋E-1～E-3、8-1～8-5＋E-1～E-3、9-1～9-7、10-1～10-9＋E-1～E-5、11-3/E-3/E-4、12-1～12-4、13-1～13-7、14-1～14-6＋E-1～E-4、15-6～15-8＋E-1～E-4、16-1～16-5、17-1～17-8＋E-1～E-4、18-1～18-9＋E-1～E-5、19-1～19-6＋E-1～E-4、20-1～20-8＋E-1～E-4、21-1～21-4、23-1～23-7＋E-1/2（標題）、24-1～24-6＋E-1～E-3、25-1～25-5＋E-1/2、26-1～26-4＋E-1/2、27-1～27-3＋E-1/2、28-1～28-8＋E-1～E-3、29-1～29-5＋E-1～E-3、30-1～30-5＋E-1/2。
判讀：載具與指令格式一致（pytest `-k`、gradle `--tests`、vitest `-t`）；前置符號在工作樹存在（`parse_frozen_prd` scr.py:68、`validate_research_approver` sdd_cli.py:397、`INNER_TRANSITION_TARGETS` :356、`INNER_GATES` :370、`project_state` orchestrator.py:398、`reconcile_at_route` research.py:1150、`child_env` gitops.py:317、`redact` gitops.py:92、`write_text_atomic` fsutil.py:20、`MiniResearch`、`ResearchFixtures`、`BridgeSource`、`repo_writable` route.py:54；`redact_secrets` 在 AutoClaude `utils/redaction.py:73` 且 Bridge 已匯入 autoclaude 套件）。不可執行或不確定：F-06、F-07、F-08、F-11。其餘 Then 皆可機械判定、hermetic（假 gh、`file://` bare repo、暫存 FSM、拋棄式 DB）。

## E 硬釘重掃（逐項對現檔）
| 項 | 現值（我重掃） | TCS | 結果 |
|----|---------------|-----|------|
| OpenApiIT | :170 107、:171 124、:971 hasSize(30)、:979 35、:980 34、:999 35 | §4 #6～10 | 符 |
| RbacIT | `security/RbacIT.java:459-478` 九條規則已含 gates／delivery/tag／delivery/pr；:499 探針已含；SecurityConfig :107-109 已預登 | #14 | 符 |
| ResearchReasonsTest | :142 35、:60／:63 兩份 PENDING；P0 22＋P0_TAIL 4＋P1 9 | #11、12 | 符；前端 `research.test.ts:959` 漏列（F-04） |
| Flyway 版本清單 | SchemaMigrationIT:69、V5Upgrade:136、IssuePriority:131、BackupJob:171／191、SiConsoleWrites:129、ResearchSchemaMigrationIT:502／1739／505／1032 | #1～3 | 符；V20 為現行最大 |
| `research_pg_support.LAST_VERSION` | :30＝20 | #19 | 符 |
| BackupJobMigrationIT 排除 | :85-89 `research\_%`、`v\_research\_%`、`console.research\_%` | #5 | 符，V21 不需改 |
| test_sdd_cli | :274、:388-394 | #28 | 符（不變） |
| CAPABILITY／EXEC_MODULES／AST | `test_research_ast_locks.py` :31、:360、:424-425、:443-445（呼叫者 2）；capability `EXEC_DOORS` :117 | #21～25 | 符 |
| 對帳呼叫點鎖 | `test_research_reconcile.py:331-339` | 無 | **漏（F-02）** |
| CHECK_IDS 跨語言 | reconcile.py:53；`MiniResearch.java:226,240`；`research-docker.stack.spec.ts:339-346`；`research.ts:518-525`＋`research.test.ts:710-714`；`test_research_reconcile.py:99-101` | #15、20 只含部分 | **漏三處（F-03）** |
| gitops 測試 | `test_research_gitops.py:113,116`；`_MESSAGE_RES` gitops.py:165、parse_git :174、parse_gh :286 | #23、24 | 符 |
| db.py | INSERT :272、:1122；P1_OPS :1355、ROUTE_OPS :1370、OPS :1383、查找鏈 :1451；`test_research_db.py:154-158` | #26 | 符；`EVENT_PAYLOAD_KEYS` 漏（F-10） |
| 假 gh | gh_fake.py:30-43 只認 auth status、repo create | #27 | 符 |
| 端點函式數 | `endpoints.test.ts:322`＝118 | #31 | 符 |
| 導覽／說明 | research-nav.test.ts:118-119,125；registry.test.ts:138-146 前綴比對 | #39 | 符 |
| 漂移橫幅 | ResearchWorkspaceView.tsx:92、BuildFrontPanel.tsx:43、PlaceholderPanel :66、ResearchFlowHeader.test.tsx:123 | #34～36 | 符 |
| InnerLoopLinks | :36 `/execute`、:51 `/monitor` | #37 | 符 |
| 事件型別前端 | `RESEARCH_SSE_EVENT_TYPES` 已含 `research.delivery`（research.ts:867） | — | 符 |
| 框架側常數 | `transition_rules.py:267-275` RETRY_LIMITS（PR_REVIEW 5、RTM_VERIFY 2、RELEASE_READY 2）、:311 RELEASE_READY→RELEASE | AT-962-3-3～3-5 | 符 |
| 研究 reason 與契約鎖 | 新增 `no_console_project`／`prd_not_frozen`／`preview_ack_required` 皆為 `details` 項名或 `violations.rule`，不是 reason | ⚖P2-6、12、13 | 符，四方鎖 37 不變 |

## F V21 DDL 草案核對
| 項 | 結果 |
|----|------|
| gate CHECK 加 SCG6 | 齊備：DO 區塊先驗 `research_gate_decisions_gate_check` 存在、DROP 後重加八值。V18:140 是欄位層級匿名 CHECK，PostgreSQL 預設名即此（推論，未對 DB 實跑）；V18:152 的表級 CHECK 是另一條，不衝突；VARCHAR(11) 容得下 |
| `details JSONB NOT NULL DEFAULT '{}'`＋object CHECK | 齊備（`ck_research_gate_details_object`）；append-only 守衛不觸發 ADD COLUMN |
| `snapshot_sha256 CHAR(64)`＋64 hex CHECK | 齊備（`ck_research_deliveries_snapshot_sha256`）；V19:96-111 的 research_deliveries 無此欄 |
| `evidence_url`＋https＋≤500 | 齊備（`ck_research_scr_evidence_url`）；V16:79-87 受控更新守衛以 `to_jsonb(NEW)-allowed` 比對，新欄自動屬清單外，驗收段 #19 成立 |
| 不動 V1～V20、無新表 | 是；V16～V20 已存在，V21 未存在 |
| 驗收段逐 CHECK 一個斷言 | 25 列，gate 八值／越界、details 四種、snapshot 63／65／大寫／g、evidence 四種加 501、守衛、回填、型別皆有；對應 AT 皆存在 |
| 約束名 | `ck_` 前綴為新增命名（V16～V20 無具名 CONSTRAINT），無衝突 |
缺口：無（P2 以上 0）。誠實劃界：DDL 未對真庫實跑，主控落 K.6 前以 Testcontainers 或拋棄式 DB 套 V1～V21 一次。

## G 誠實劃界與其他核對
- 編號與文法：AT 297（§1.5 297＝§3 297＝RTM 297，皆唯一、無漏）；正控 199＋負控 98；AC 30；RTM 定義列 331＝1＋3＋30＋297，四格皆 ⬜；撞號 `git grep -E 'F-908|US-92[678]|AC-962|AT-962|AT_962' -- AgentConsole docs` 0 命中；每 AT 有 Given／When／Then／判定（腳本核對缺 0）。
- 守門：三份檔在 `通過|略過|tests` 與四位數字同行的雙向正規式零命中；LF（CR 0）。
- 出口 (a)～(i)：§6.1 九項皆指到存在的 AT 或 V（(c)(i) 受 F-11 影響證據面）。
- 未做：未對 TCS 全部 297 個 AT 逐條實讀（讀約 110 個，其餘靠結構核對）；未實跑任何測試或 DDL；Java／TS 的 Then 是否與未來實作相容屬推論。
- D-142 其餘項（⚖P2-1、6、8、10～14、17、18）：條文與 D-142 一致（delivery.py 零 FSM 寫入、SCG6 納入 gates[]、`RESEARCH_REASONS` 住 research.ts 等）；僅 ⚖P2-9、⚖P2-15 與 D-142 衝突。
- 殘留：只在 `S\qa\p2\` 建了腳本與 JSON；無 repo 變更、無行程、無資料庫。


---

# 〈二審〉（範圍：一審 F-01～F-13 修法、新增 12 個 AT、§4 新列、計數同步；未動條文不重審）

## 二審判定：FAIL（P1 0、P2 1、P3 1、P4 2）
一審 P2 六條全數落地；殘留 1 條 P2 是「§4.4 勘誤指示與 D-145 相反」，修一行即可 PASS。

## 一審逐條核對
| F | 結果 | 證據（對現檔） |
|---|------|----------------|
| F-01 | 已修 | W-R2P9、§7 ⚖P2-9（採納 D-142 改判）、AC-962-8 Then、AT-962-8-4、18-E-5（422、零副作用、漂移先於 FSM／RTM 前置、現態不合加漂移回 422）、新 3-E-6（三種 gate 負控）、4-E-5、19-E-5（console-api 透傳）、26-E-1（檢查序加漂移）；`digest_mismatch` 在 P0 reason 內，四方鎖仍 37 |
| F-02 | 已修 | §4 第 31 列：`test_research_reconcile.py:331-339`（我核實 :331 函式名、:339 `["app/routers/research.py"]*3`）；AT-962-23-4、⚖P2-15 同步 |
| F-03 | 已修 | §4 第 32 列（:99-101，我核實為六鍵字典）、第 44 列（`research-docker.stack.spec.ts:339-346`，例外只改名單，FE-W3 允許集合已補列）、第 46 列（`research.ts:518-525`、`research.test.ts:710-714`，FE-P2A）；AT-962-23-7 |
| F-04 | 已修 | §4 第 35 列加 `research.test.ts:958-959`（核實為 `toHaveLength(35)`）；AT-962-24-6 Then 加 37 |
| F-05 | 已修 | AC-962-4 加 UI 半；新 vitest AT-962-4-7、4-8、4-E-6、4-E-7、4-E-8、4-E-9（獨立聲明、FAIL 理由與 500／501、300／301、RELEASE_READY 只有 FAIL、SCR_OPEN 停用、非 ADMIN、錯誤文案）；負控 4 個；`GateRegisterDialog.test.tsx` 在 FE-P2A 允許集合 |
| F-06 | 已修 | AT-962-13-2 限非測試原始碼、剝註解、字串拼接組正則 |
| F-07 | 已修 | AT-962-28-3 改 `run_body`＋`claude.command`＋`MOCK_CLAUDE_FAIL_REGEX`（conftest.py:236-244、mock_claude.py:19 仍在） |
| F-08 | 已修 | AT-962-3-E-5 單值 503 `db_blocked`；`outbox.py:263,:285` 核實為 `DbBlocked`；⚖P2-19 追認，D-145 一致 |
| F-09 | 已修 | 20-2（3999／4000／4001）、18-2（2000／2001）、11-3 與 13-6（501ms 負控）、9-2（maxRetries -1／0／+1） |
| F-10 | 大部分 | 六鍵 `{kind, ref, status, digest, reason, failure_step}` 見 18-4、22-3、26-5（含失敗四種與缺鍵、未登記鍵）、§4 第 33 列（`db.py:67-87`、:89、:349-357、`test_research_events.py:195,:282` 核實）；`test_research_events.py` 已入 BR-P2 允許集合；**但 §4.4 E1 仍寫 `payload 補 commitSha、traceabilitySha256`（見 F-14）** |
| F-11 | 已修 | AT-962-28-5 載具甲＋`approveViaApi`（`tests/helpers/research-stack`，research-docker.stack.spec.ts:13 已匯入），證據標明代驗 |
| F-12 | 已修 | 新 18-E-6（Bridge）、19-E-6（console-api）；28-8 保留 |
| F-13 | 已修 | §7 待裁決列數 0；AC-R2P-19-7 納入 §1.2 第 286 列與 AT-962-15-3 標題；7-3 改為「檔名 glob 計數為 1」；`SecurityConfig.java:107-109` 經核實確指三條 gates／tag／pr 規則（一審我標 P4 為誤判，撤回） |

## 新發現（二審）
| F | 嚴重度 | 座標 | 問題 | 修法（指名 SD） |
|---|--------|------|------|----------------|
| F-14 | P2 | §4.4 E1，TCS 第 2304 行 | 勘誤內容仍寫「payload 補 `commitSha`、`traceabilitySha256`」。D-145：`research.delivery` 固定六鍵、`commitSha` 不在事件；18-4／22-3／26-5 已是六鍵。照 E1 落勘誤會把契約寫成與 AT 相反。 | SD 修：E1 改「payload 固定六鍵 `{kind, ref, status, digest, reason, failure_step}`」，`commitSha` 只在 `research_deliveries` 列 |
| F-15 | P3 | AT-962-23-7，L2030 | Then「`ResearchReconcileCheck` 型別聯集含 `delivery`」：`lib/api/types.ts:840-845` 的 `name` 是 `string`，沒有聯集可驗。 | SD 修：刪該句，或改為「`RECONCILE_CHECK_LABEL` 含 `delivery` 且 `reconcileDriftView` 對 delivery drift 回檔案漂移列」 |
| F-16 | P4 | AC-962-4 Then | 寫「前置（漂移…）先於 Bridge 副作用檢查」，但 console-api 不自比 digest（19-E-5），漂移由 Bridge 判定；字面易誤導。 | SD 順手改 |
| F-17 | P4 | AT-962-4-E-9 | 「403 取 RESEARCH_REASON_TEXT」：403 在授權鏈是 `ACCESS_DENIED`，不屬研究 reason，登記處無對應文案可驗。 | SD 順手改（指明 403 取通用權限不足文案） |

## 計數與守門（我獨立核）
- AT：§1.5 309＝§3 309＝RTM 309；正控 202＋負控 107；AC 30；RTM 定義列 343＝1＋3＋30＋309，唯一、四格皆 ⬜、與 TCS 集合雙向差集空；檔頭第 46 行宣告一致。
- PRD P2 AC-R2P：38 條（核心 23＋增量 15，含 19-7）皆有 AT；§1.2 與 §3 標題列引用集合相等。
- 新增 AT 12 個（3-E-6、4-7、4-8、4-E-5～4-E-9、18-E-6、19-E-5、19-E-6、26-5）；變更 19 個；每 AT 皆有 Given／When／Then／判定（缺 0）。
- 守門正規式雙向 0 命中；三份檔 CR 為 0；`git grep -E 'F-908|US-92[678]|AC-962|AT-962|AT_962' -- AgentConsole docs` 0 命中。
- SD 自檢 SELF_CHECK.md 自述 53／53 通過（其 rc 我無法複驗：selfcheck.py 會覆寫檔案，違唯讀，故未執行；以上為我獨立重算）。

## 誠實劃界
只審一審修法與新增／變更 AT（我以前後解析 JSON 差異鎖定 12 新增＋19 變更）；未重審未動的 278 個 AT；未跑任何測試或 DDL；V21_DDL.md 未再變動（修改時間早於 TCS 末次修改），一審結論沿用。


---

# 〈三審〉（範圍：二審 F-14～F-17 四處；其餘不重審）

## 三審判定：PASS（P1 0、P2 0、P3 0、P4 0）
| F | 座標（現檔） | 結果 |
|---|-------------|------|
| F-14 | §4.4 E1，:2304 | 已修：payload 定為固定六鍵 `{kind, ref, status, digest, reason, failure_step}`，`commitSha` 只在 `research_deliveries` 列、不進事件，與 D-145、18-4、22-3、26-5 一致；全檔無殘留「commitSha、traceabilitySha256 補入 payload」字樣 |
| F-15 | AT-962-23-7，:2030 標題、:2033 Then | 已修：改為 `RECONCILE_CHECK_LABEL` 含 `delivery`＝『交付』與 `reconcileDriftView` 對 delivery drift 回檔案漂移列，並註明 `types.ts:840-845` 的 `name` 為 `string`、不需型別聯集；無殘留「型別聯集含」 |
| F-16 | AC-962-4 Then，:143 | 已修：「漂移由 Bridge 判定、console-api 只透傳 422」，與 19-E-5、4-E-5 一致 |
| F-17 | AT-962-4-E-9，:1690 與 §1.5 :387 | 已修：403 `ACCESS_DENIED` 取通用權限不足文案（非研究 reason），其餘取 RESEARCH_REASON_TEXT；兩處一致 |

守門自掃：AT §1.5＝§3＝309、RTM 定義列 343（1＋3＋30＋309）；每 AT 有 Given／When／Then／判定；`通過|略過|tests` 加四位數字正規式雙向 0 命中；TCS、RTM、V21_DDL 三檔 CR 皆 0；`git grep -E 'F-908|US-92[678]|AC-962|AT-962|AT_962' -- AgentConsole docs` 0 命中。未動條文與 V21 草案不重審，沿用前兩審結論；未跑測試或 DDL。
