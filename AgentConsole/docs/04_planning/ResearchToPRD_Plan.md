輸入快照：HEAD＝01d9be6e；主控裁決 D-01～D-66

# ResearchToPRD 計畫書（分期、鎖持有面、派工波次與出口閘）

**版本**：v1.0.0-rc3 定稿候選｜**日期**：2026-11-02｜**作者**：Architect 草擬分期、SD 依主控裁決 D-12～D-66 定稿
**依據**：根 `CLAUDE.md` 鐵律七〈並行派工防互踩檢查表〉（結案單線／修復棒串行／複審唯讀／收尾單人窗口）與〈派工模型〉（子代理一律 `model: sonnet`、不用 `fork`）；`SDD_AUTOCLAUDE_BRIDGE.md` §8（一功能一鍵、一視窗一功能）；PRD `docs/01_requirements/ResearchToPRD_PRD.md`（§8.1 出口判準為本計畫的上位）。
**指令形態**：一律 PowerShell；每個區塊自行 `$root` 起手；讀 rc 先存變數、不接管線；不裸 `cd`（用 `Push-Location`／`Pop-Location` 同呼叫成對）；Windows 禁用 Bash 工具。

---

## 1　分期總表

| 期 | 目的 | 鍵（hooks-ON 視窗） | 入口條件 | 出口閘（全綠才收） |
|----|------|---------------------|---------|-------------------|
| **W0 規格波**（單視窗，串行） | PRD、Architecture 增補、API 契約、ADR-003／ADR-XPLAT-017、Console PRD §0.9／§8.1、P0 TCS 凍結、`.gitignore` 與 CI paths 等根層連動 | 開發本 repo 的鍵＝`agentconsole-research-to-prd-p0`（`sub=agentconsole`；slug 18 字 ≤30，BRIDGE §8.0:341） | 主控裁決 D-12～D-66 已有（掌舵者授權代決） | SCG-0～3 對應的 SA／SD／QA 獨立審查 PASS；Stage-1 基線採納（BRIDGE §8.4:511 的 agentconsole 上位文件表）＋Stage-2 TCS `spec-frozen`；`docs/06_quality/` 有 SCG-0 審查報告 |
| **F 框架波**（與 W0 後段／P0 並行，**另一視窗另一鍵**；先於 P0 整合驗收，P0 單元測試以夾具先行、不阻塞；D-33） | 框架側方法層（1 workflow、2 agent、4 模板、SCG-0 評分協定、SCR 路徑、BRIDGE §8.0／§9 增補、框架 ADR-001） | `sdd-research-to-prd`（`sub=sdd`；框架窗 `$slug='research-to-prd'`） | W0 的 PRD 草案定案（框架文件引它） | `framework_status_snapshot.py --check` rc 0、`ci-gate.ps1` rc 0、邊界核對（ADR-XPLAT-017 §D7）、SCG-4 獨立審查 |
| **P0 外環** | 研究→證據→PRD→四方審查→Gate 0；頁面脊 ①②；DB V16～V18；Bridge 研究套件與 ADR-XPLAT-017 的 Bridge 側實作 | `agentconsole-research-to-prd-p0` | W0 出口＋F 波的 agent／模板檔已入 LATEST（Bridge 編譯期讀得到；單元測試以夾具為準） | 見 §3 P0 出口（＝PRD §8.1 P0 列） |
| **P1 分流** | 軌道 A／B、Stage-1 採納、TCS 草擬與凍結（D-33）、SCR 後端、步驟 ③、步驟 ④ 前半；V19（分流、SCR、拆解、交付表與自癒視圖，一次建立） | `agentconsole-research-to-prd-p1` | P0 RELEASE（含雲端 CI 綠）；P0 的 Gate-0 在真機走通一次 | 見 §3 P1 出口 |
| **P2 內環看板與交付** | 看板五格、自癒監視、終端窗格、HITL、SCG-4／SCG-5 登錄、交付（tag／PR／開本地專案）、`ResearchBackLink`、SCR 發起鈕與橫幅；V19 只寫列 | `agentconsole-research-to-prd-p2` | P1 RELEASE；至少一個研究專案有內環 run | 見 §3 P2 出口 |

每鍵一個週期、收尾記一次 `RELEASE`；下一期用新鍵新視窗（BRIDGE §8.0:340、§8.7:552）。**徑判定**：Bridge（Python）可走徑①委派迴圈；backend（Java）與 frontend（TS）走徑②「SDD session-only」（BRIDGE §7:312-313）——AT 由 session 內自跑 `gradlew test --tests …`／`vitest run -t …`／`pytest -k …`，**輸出逐字貼進證據檔與 RTM**（沒貼＝未驗證）。

---

## 2　每期交付物

### W0（文件，單窗，主控／SA／SD／QA 序列；子代理 Sonnet 且不並行——複審唯讀）
| 檔 | 內容 |
|----|------|
| `docs/01_requirements/ResearchToPRD_PRD.md` | PRD（回指來源規格章節；§9.0 附**模組落點表**——本功能屬子專案模組，落 AgentConsole／AISDLC_SDD，不往根層放；`Root_Layout_and_Module_Placement.md` §2） |
| `docs/01_requirements/ResearchSOPtoPRD_Source_Spec.md` | 來源規格逐字檔（掌舵者原文；PRD 多處以「來源 §x.y」回指其章節）。**主控預先落檔、W0 同 commit 收入**（落檔 commit 一併 `git add`；先於各鍵 Stage-1 採納的基準 commit，故不在 ADR-XPLAT-017 §D7 的根層例外清單內） |
| `AgentConsole/docs/02_architecture/Architecture.md` | 本輪增補：§2.2、§3、§5.1、§5.4、§6(e)、§7.2、§8.2～8.4、§9.4、§10.1～10.3、§11.1、§11.3（DDL 全文）、§12.1～12.2 |
| `AgentConsole/docs/02_architecture/API_Contract_ResearchToPRD.md` | 定稿 v1.0 |
| `AgentConsole/docs/02_architecture/ADR-003-ResearchToPRD.md` | AgentConsole 側決策 D1～D16 |
| `docs/04_planning/ADR/ADR-XPLAT-017-bridge-fsm-write-surface.md` ＋ ADR-XPLAT-016 回寫 | 附錄 B 的兩處註記（§3.5 列尾、附錄 F） |
| `docs/01_requirements/Agent_ConsoleUI_PRD.md` §0.9／§8.1 註 | §0.9 新增（權威區塊，接在 §0.8 之後）與 §8.1 導覽註一行；不新增目錄行（目錄不列 §0 子節） |
| `AgentConsole/docs/03_testing/contracts/TCS-ResearchToPRD-P0-<日期>.md` | P0 TCS（含增量追溯表；AT 以 `AT-96N-…` 配號，**Java／TS 的 AT 不入 evaluator**）。本地編號避撞：落檔當下現查 `AgentConsole/docs/03_testing/contracts/` 全檔，2026-11-02 讀到的最大值＝F-905、US-919、AC／AT 家族號 953；P0／P1／P2 建議各取 960／961／962 作 AC／AT 家族號、F 自 906 起、US 自 920 起 |
| `AgentConsole/docs/04_planning/Implementation_Plan.md` §5.1 | 進度帳增列（附錄 B） |
| `AgentConsole/docs/06_quality/RTM-ResearchToPRD-P0-<日期>.md` ＋ `RTM.md` 存根 | 子表自始立於獨立檔，`RTM.md` 只放標題行＋一行引言的存根（DEF-200-576 體例；先例＝`RTM.md:488-492` 的 §2.8、§2.9 與 `AgentConsole/docs/06_quality/RTM-ExecMonitorEntry-20261101.md:1-7` 的檔頭）；本功能存根接在 §2.9 之後（§2.10 起，每期一份）；子表內 ID 欄加反引號、不計入 §2 總列數與 US 58（D-34） |
| `AgentConsole/CLAUDE.md`（鐵律 7） | 白名單句加 ADR-XPLAT-017 §D7 引用（主控） |
| `.gitignore`（根）、`.github/workflows/agentconsole-ci.yml` `paths`、`docker-compose.yml`、`.env.example` | **主控代做**（根層檔；`AgentConsole/CLAUDE.md` 鐵律 7 禁開發棒碰）：`.gitignore` 加 `/my-project/`；`paths` 兩處（`on.push.paths`＝`agentconsole-ci.yml:21-35`、`on.pull_request.paths`＝`:38-52`；兩份清單內容相同、須同步）加 `AISDLC_SDD/*/agent/**`、`AISDLC_SDD/*/docs_template/sdd/requirements/**`、`AISDLC_SDD/*/workflow/sdd-research-to-prd/**`（沿既有 `AISDLC_SDD/*/tools/fsm_runtime/**` 的星號寫法，見 `:28`、`:45`）；compose／`.env.example` 加 `BRIDGE_RESEARCH_*`（Architecture §9.4） |

### P0
- **DB**：V16、V17、V18（含 `research_gate_decisions`、`research_allowlist_entries`）；`ResearchSchemaMigrationIT`（新類別；既有 `SchemaMigrationIT` 只改 Flyway 版本清單）套用成功＋每個 CHECK／觸發器斷言；另四個既有 IT 的 Flyway 版本清單斷言、`OpenApiIT` 的路徑總數釘選與 `BackupJobMigrationIT` 的 `snapshotOfExistingTables` 前後快照相等斷言（查詢須排除 `research_%`；D-65）須同包同步（§4 鎖表 L4）。
- **Bridge**：`app/research/{settings,db,outbox,layout,fsm_ops,export,orchestrator}.py`、`fetch/*`、`compile/*`、`gates/*`＋`gate_cli.py`、`routers/research.py`（P0 端點含 allowlist）；`sdd_cli.py` 研究面動詞（ADR-XPLAT-017 D2）；`settings.py` 與 README 環境表；`/health/deep` 加 `research` 資訊欄（含 `mode`）。原子寫檔一律**重用 `fsutil.write_text_atomic`**（`fsutil.py:20-26`，既有 `os.replace` 站點），**不新增** `os.replace`／`rename`／`move`（否則要動根層 `TestDirEntryPrimitivesAreAccountedFor`，那是 `tools/tests`，開發棒不得碰）。
- **console-api**：`ResearchController`（P0 端點）、讀配接器、`ResearchQuery／CommandService`、`ResearchFlowPolicy`、`StreamController` 研究串流、`BridgeHttpAdapter` 方法、`AuditTrail.note` 標註、`SecurityConfig` ADMIN matcher（置於通用規則之前）、`OpenApiIT`／`RbacIT`／`ErrorResponseDocumentation`、`console.bridge.research-write-token` 屬性。
- **frontend**：兩條路由、導覽列與說明兩條、`FlowStepper`／`ResearchFlowHeader`、`TopicPanel`／`EvidenceTimeline`／`EvidenceMatrixTable`／`AllowlistDialog`、`StudioPanel`／`PrdOutline`／`PrdDiffView`／`MermaidBlock`／`GatekeeperPanel`、`SddEscalationBlock` 重用；相依 `mermaid`、`diff`；`schema.d.ts` 重產。
- **框架**：F 波全部。
- **文件**：TCS 增補、RTM 回填、Architecture §5.1／§7／§10／§11 落地註記。

### P1
V19（`research_route_decisions`／`_route_steps`／`research_scr`／`research_decompositions`／`research_deliveries`、視圖 `v_research_healing_attempts`）；Bridge `route.py`／`scaffold.py`／`gitops.py`／`scaffold_templates/python-fastapi/`／`scr.py`、`tcs-draft` stage、`:route`／`:scr`；console-api 分流與 SCR 端點（先建 `projects` 列再呼 Bridge、失敗補償）；frontend `RouteDrawer`、③面板、④前半（TCS 草擬／核准、連到既有 freeze／import／execute）；`capabilities` 探針的 UI 停用；文件：TCS-P1、RTM-P1、ADR-003 補記。

### P2
Bridge `release.py`、`:gates`／`:tag`／`:pr`；console-api 交付與 SCG 登錄端點；frontend `BuildPanel`（看板五格、自癒監視、終端窗、HITL 手動回報）、`DeliverPanel`（重用 `RtmPanel`）、`ResearchBackLink`（置於兩個頁殼，View 本體零改）；`NotificationBell` 納入「待人工決定」；文件：TCS-P2、RTM-P2、Architecture 收尾註記。

---

## 3　每期出口閘（具體指令；證據逐字貼進證據檔）

本節每段指令皆 PowerShell 與 bash 並列（`AgentConsole/CLAUDE.md` 跨平台鐵律 1）；Windows 一律走 PowerShell 形態（禁用 Bash 工具、禁裸 `cd`），bash 形態給 mac／Linux。讀 rc 一律緊接在該指令之後、不接管線。

### 通用（每個區塊自行起手）
```powershell
$root = (git rev-parse --show-toplevel); $py = Join-Path $root '.venv\Scripts\python.exe'
```
```bash
root="$(git rev-parse --show-toplevel)"; py="$root/.venv/bin/python"
```

### Bridge（Python；P0／P1／P2 皆跑）
```powershell
$root = (git rev-parse --show-toplevel); $py = Join-Path $root '.venv\Scripts\python.exe'
Push-Location (Join-Path $root 'AgentConsole\engine-bridge')
& $py -m pytest -q; $rc_pytest = $LASTEXITCODE
& $py -m ruff check .; $rc_ruff = $LASTEXITCODE
Pop-Location
& $py -m ruff check (Join-Path $root 'AgentConsole\engine-bridge'); $rc_ruff_root = $LASTEXITCODE
Push-Location (Join-Path $root 'tools\tests')
& $py -m unittest test_platform_neutral_paths.TestDirEntryPrimitivesAreAccountedFor -v; $rc_dirent = $LASTEXITCODE
Pop-Location
"pytest rc=$rc_pytest ruff rc=$rc_ruff ruff(root view) rc=$rc_ruff_root dirent rc=$rc_dirent"
```
```bash
root="$(git rev-parse --show-toplevel)"; py="$root/.venv/bin/python"
(cd "$root/AgentConsole/engine-bridge" && "$py" -m pytest -q; echo "pytest rc=$?")
(cd "$root/AgentConsole/engine-bridge" && "$py" -m ruff check .; echo "ruff rc=$?")
"$py" -m ruff check "$root/AgentConsole/engine-bridge"; echo "ruff(root view) rc=$?"
(cd "$root/tools/tests" && "$py" -m unittest test_platform_neutral_paths.TestDirEntryPrimitivesAreAccountedFor -v; echo "dirent rc=$?")
```
（`AgentConsole/CLAUDE.md` 閘門清單的 engine-bridge 列：ruff 兩視角、pytest、`GET /health`、根層 dirent 鎖、`docker build`。）另跑：`tests/test_cross_platform_guard.py`（子行程 helper 使用）、`tests/test_sdd_cli.py`（動詞表）。

### backend（Java；徑②）
```powershell
$root = (git rev-parse --show-toplevel)
Push-Location (Join-Path $root 'AgentConsole\backend')
.\gradlew.bat test --tests '*Research*'; $rc_t = $LASTEXITCODE
.\gradlew.bat clean build; $rc_b = $LASTEXITCODE        # JaCoCo ≥80%、ArchUnit、Flyway＋ddl-auto=validate
Pop-Location
"test rc=$rc_t build rc=$rc_b"
```
```bash
root="$(git rev-parse --show-toplevel)"
(cd "$root/AgentConsole/backend" && ./gradlew test --tests '*Research*'; echo "test rc=$?")
(cd "$root/AgentConsole/backend" && ./gradlew clean build; echo "build rc=$?")   # 出現 Permission denied 改 sh gradlew
```

### frontend（TS；徑②）
```powershell
$root = (git rev-parse --show-toplevel)
Push-Location (Join-Path $root 'AgentConsole\frontend')
npx vitest run lib/nav lib/help components/domain/research lib/domain; $rc_v = $LASTEXITCODE
npm run lint; $rc_l = $LASTEXITCODE
npx tsc --noEmit; $rc_s = $LASTEXITCODE
npm run build; $rc_bd = $LASTEXITCODE
Pop-Location
"vitest rc=$rc_v lint rc=$rc_l tsc rc=$rc_s build rc=$rc_bd"
```
```bash
root="$(git rev-parse --show-toplevel)"
(cd "$root/AgentConsole/frontend" && npx vitest run lib/nav lib/help components/domain/research lib/domain; echo "vitest rc=$?")
(cd "$root/AgentConsole/frontend" && npm run lint; echo "lint rc=$?")
(cd "$root/AgentConsole/frontend" && npx tsc --noEmit; echo "tsc rc=$?")
(cd "$root/AgentConsole/frontend" && npm run build; echo "build rc=$?")
```

### 框架（F 波；在 `sdd-research-to-prd` 視窗與收尾單人窗口跑）
```powershell
$root = (git rev-parse --show-toplevel); $py = Join-Path $root '.venv\Scripts\python.exe'
& $py (Join-Path $root 'AISDLC_SDD\scripts\framework_status_snapshot.py') --write; $rc_w = $LASTEXITCODE   # 同 commit 最後一步
& $py (Join-Path $root 'AISDLC_SDD\scripts\framework_status_snapshot.py') --check; $rc_c = $LASTEXITCODE
& $py (Join-Path $root 'AISDLC_SDD\scripts\sync_exposed_skills.py') --check; $rc_k = $LASTEXITCODE        # skills 鏡像未動，仍須確認沒漂
powershell -ExecutionPolicy Bypass -File (Join-Path $root 'AISDLC_SDD\scripts\ci-gate.ps1'); $rc_g = $LASTEXITCODE
"snapshot write rc=$rc_w check rc=$rc_c skills rc=$rc_k ci-gate rc=$rc_g"
$base = '<起點 commit>'    # 由主控記錄；兩條核對的輸出各自貼證據
git diff --name-only $base HEAD -- AISDLC_SDD
git diff $base HEAD -- 'AISDLC_SDD/*/tools/fsm_runtime/transition_rules.py' 'AISDLC_SDD/*/tools/fsm_runtime/formal'   # 必須無輸出
```
```bash
root="$(git rev-parse --show-toplevel)"; py="$root/.venv/bin/python"
"$py" "$root/AISDLC_SDD/scripts/framework_status_snapshot.py" --write; echo "snapshot write rc=$?"   # 同 commit 最後一步
"$py" "$root/AISDLC_SDD/scripts/framework_status_snapshot.py" --check; echo "snapshot check rc=$?"
"$py" "$root/AISDLC_SDD/scripts/sync_exposed_skills.py" --check; echo "skills rc=$?"
(cd "$root/AISDLC_SDD" && bash scripts/ci-gate.sh; echo "ci-gate rc=$?")
base='<起點 commit>'    # 由主控記錄；兩條核對的輸出各自貼證據
git diff --name-only "$base" HEAD -- AISDLC_SDD
git diff "$base" HEAD -- 'AISDLC_SDD/*/tools/fsm_runtime/transition_rules.py' 'AISDLC_SDD/*/tools/fsm_runtime/formal'   # 必須無輸出
```

### Docker 全棧 E2E（mock claude；真研究不在此）
```powershell
$root = (git rev-parse --show-toplevel)
Push-Location (Join-Path $root 'AgentConsole')
docker compose --profile db --profile app --profile full up -d --build; $rc_up = $LASTEXITCODE
Pop-Location
"compose up rc=$rc_up"        # 之後以 Playwright（nginx 80 埠；E2E_ROOT 短路徑；並行須各自 --output）跑研究 E2E；收尾 down（不帶 -v）
```
```bash
root="$(git rev-parse --show-toplevel)"
(cd "$root/AgentConsole" && docker compose --profile db --profile app --profile full up -d --build; echo "compose up rc=$?")
```

### 出口判準
- **P0 出口**：PRD §8.1 的 P0 列 (a)～(i)：①Bridge／backend／frontend 三閘 rc 0 ②AT 清單（API 契約 §5 的 20 條＋TCS 其餘）逐字貼證據 ③Docker E2E：mock claude 跑通 `建立→research→draft→review×3(FAIL)→ESCALATED` 與 `建立→…→review PASS→approve→FROZEN` 兩條，SSE 斷線重播無缺漏（API 直呼 `stages/research`，UI 在 mock-only 停用「啟動深研」）④**真機本機模式**驗收一次（Windows、真 claude）：V-R1／V-R2／V-R3／V-R5 的結果與 V-R9 殘餘（僅 Stack Exchange）入證據檔；Gate 0 後 `show --must-exist` 逐字輸出入證據（`frozen_stages[*].spec_doc_digests` 與 `research_gate_decisions.frozen_digests` 逐位元相同）⑤SCG-4 獨立審查（QA 鏡，Sonnet，未參與規格與實作）PASS ⑥RTM-P0 回填、`CLAUDE.md` ≤200 行／`README.md` ≤80 行（`AgentConsole/CLAUDE.md` 閘門清單）。
- **P1 出口**：P0 全項不退步＋PRD §8.1 的 P1 列 (a)～(k)：軌道 A（目標＝本 repo 的**拋棄式 clone**，真 git、不動真 repo）與軌道 B（暫存 `BRIDGE_SCAFFOLD_ROOT`、`gh` 以假指令替身）各一次端到端，另掌舵者以 Private 測試庫真機一次軌道 B；內環鍵 Stage-1／Stage-2 `show` 逐字證據；SCR MINOR 一次序列證據（ADR-XPLAT-017 附錄 A 的指令序列）；`capabilities` 缺 `gh`／scaffold 時 UI 停用的 AT。
- **P2 出口**：P1 全項不退步＋PRD §8.1 的 P2 列 (a)～(i)：一個研究專案走完 內環 run→PR_REVIEW→RTM_VERIFY→RELEASE_READY→`RELEASE`（暫存專案）；`v_research_healing_attempts` 對真失敗步驟有列；tag 動作以暫存 git 驗；`ResearchBackLink` 兩頁 AT。

---

## 4　鎖持有面表（鐵律七：每包列「常數／史料／消費端」住哪幾支檔；三者不在同一持有面的包不得並行）

| # | 鎖／棘輪 | 常數（住哪） | 史料（住哪） | 消費端（住哪） | 動它的包 | 並行規則 |
|---|---|---|---|---|---|---|
| L1 | 導覽登記表唯一性／`mobile≤6`／`DELIVERED_NAV_ROWS` 前綴／match 互斥／href 對應真路由 | `frontend/lib/nav/registry.ts`（`:42-115`；新列 `order:35`、`mobile:false`） | `frontend/tests/helpers/navDelivered.ts`；四份凍結 TCS 的「恰 N 項」陳述（IssueCenter／SysAdminBackup／ConsoleNavConsolidation／SelfImprovingMirror；以勘誤處理） | `registry.test.ts`（`:107,143,409-411`）、`ToolsRegion.test.tsx`、`layout.test.tsx` | PKG-FE-A | 與任何別的導覽改動串行 |
| L2 | 說明登記表三鎖（路由鎖／導覽鎖／頁檔鎖）＋`PENDING_CEILING` 棘輪 | `frontend/lib/help/registry.ts`（`HELP_PAGES`／`HELP_ROUTES`／`NO_STATE_PAGES`） | `registry.ts` 檔頭與 `:62-66` 的輪次註記；`lib/help/types.ts` 的 `StateTableId`（加 `researchFlow`，D-49）與 `lib/help/states.ts`（同 id 狀態表；PageHelp 既有凍結 TCS 走勘誤） | `registry.test.ts`、`content.test.ts`、`lint.test.ts`、`PageHelpButton` | PKG-FE-A（**同包，不與 L1 拆**） | 串行於 FE-A |
| L3 | Bridge FSM 動詞白名單（含 `--to` 依鍵矩陣、`gate` 四閘；`resume-from-escalation` 不入；HUMAN_PENDING 下不呼叫 `gate … PASS`，D-50） | `engine-bridge/app/sdd_cli.py`（**新增獨立的** `RESEARCH_VERBS`／`_RESEARCH_VERB_FLAGS`；既有 `ALLOWED_VERBS`／`_VERB_FLAGS`〔`:61-74`〕零改動；D-49） | ADR-XPLAT-016 §3.5:178＋ADR-XPLAT-017 §D2 | 既有 `tests/test_sdd_cli.py`（**不改**）、新增 `tests/test_research_sdd_verbs.py`、`app/research/fsm_ops.py`、`routers/research.py` | PKG-BR-A（**單棒**） | **先於** BR-C；與別的動詞改動串行 |
| L4 | Flyway 序、`ddl-auto=validate`、OpenApiIT 路徑／操作計數、`ErrorResponseDocumentation`、`RbacIT`（含 ADMIN matcher；另含 `ResearchCommandService` 對 `reinit` 帶 `generation:"next"` 的 ADMIN 角色檢查：VIEWER 回 403 `ACCESS_DENIED`〔既有授權鏈〕、OPERATOR 回 403 `research_write_forbidden`〔服務層〕，兩者 Bridge 請求數 0，D-64） | `db/migration/V16…V19`；`SecurityConfig.java` | `API_Contract_ResearchToPRD.md`、Architecture §11.3 | `ResearchSchemaMigrationIT`（新；含三種觸發器斷言，D-49、D-61）、`SchemaMigrationIT`（既有；只改 Flyway 版本清單，`AgentConsole/backend/src/test/java/com/aisdlc/console/infrastructure/persistence/SchemaMigrationIT.java:63-68`）、**另四個既有 IT 的 Flyway 版本清單斷言**（皆於套用遷移後讀 `console.flyway_schema_history` 並硬釘 `containsExactly("1", …, "15")`，V16 起即紅，須與 PKG-DB 同包同步為含新版本〔P0 到 18、P1 加 19〕；QA F-01）：`AgentConsole/backend/src/test/java/com/aisdlc/console/infrastructure/persistence/V5UpgradeMigrationIT.java:135`、`AgentConsole/backend/src/test/java/com/aisdlc/console/infrastructure/persistence/IssuePriorityMigrationIT.java:130-131`、`AgentConsole/backend/src/test/java/com/aisdlc/console/infrastructure/persistence/BackupJobMigrationIT.java:167-168`、`AgentConsole/backend/src/test/java/com/aisdlc/console/infrastructure/persistence/SiConsoleWritesMigrationIT.java:128-129`；`OpenApiIT`（含 `AgentConsole/backend/src/test/java/com/aisdlc/console/infrastructure/config/OpenApiIT.java:247` 的「本鍵不新增路徑」`hasSize(77)` 路徑總數釘選，P0 新增端點後即紅，須與 `EXPECTED` 一併同步；QA F-01）、**另一項前後快照相等斷言**（QA 二審 F-21，D-65）：`AgentConsole/backend/src/test/java/com/aisdlc/console/infrastructure/persistence/BackupJobMigrationIT.java:97,102,106,154`——V14 遷到最新版前後比較 `console` 內既有表（除 `backup_jobs`）欄位與約束的 `snapshotOfExistingTables`（`:82-90`）必須相等；V16 起新增的 `research_*` 表會進 after、不在 before ⇒ 必紅；修法是**查詢條件**的改動（查詢須排除 `research_%` 表與其約束，LIKE 的底線要跳脫），不只是預期值，須與 PKG-DB 同包同步並在 TCS 列為「不只改預期值」的例外、`schema.d.ts`（`gen:api`） | PKG-DB → PKG-API（**串行**） | DB 先；`schema.d.ts` 重產＝PKG-API 收尾 |
| L5 | AgentConsole 鐵律 7 白名單句；ADR-XPLAT-016 §11（不改） | `AgentConsole/CLAUDE.md`（鐵律 7） | ADR-XPLAT-016 §11.3:594-602＋ADR-XPLAT-017 §D7 | `git diff --name-only <起點> HEAD` 核對 | PKG-DOC0（主控） | 單窗 |
| L6 | 框架註冊表（INIT 三清單＋計數、`workflow/README.md`、`agent/specialized/README.md`）＋ FRAMEWORK_STATUS（生成） | `<SDD>/AISDLC_SDD_INIT.md`、`workflow/README.md` | `<SDD>/EVOLUTION_LOG.md`、`releases/CHANGELOG.md` | `framework_status_snapshot --check`、`arch_fitness` FF-7、`ci-gate` | PKG-F（**單棒；FRAMEWORK_STATUS 重生最後**） | 與 AgentConsole 各包可並行（不同專案、不同視窗、不同鍵；D-38） |
| L7 | 根層 dirent 鎖（`os.replace`／`rename`／`move` 站點登記） | `tools/tests/test_platform_neutral_paths.py::TestDirEntryPrimitivesAreAccountedFor` | 同檔站點表 | 同檔 | **本功能設計為不新增站點**（重用 `fsutil.write_text_atomic`；軌道 B 複製驗證、原處保留） | 若必須新增→主控收尾單窗改 `tools/`（開發棒禁碰，`AgentConsole/CLAUDE.md` 鐵律 7） |
| L8 | 根 `.gitignore`（`/my-project/`）、CI `paths`、compose／`.env.example` | 根 `.gitignore`、`.github/workflows/agentconsole-ci.yml:21-35`、`:38-52`、`AgentConsole/docker-compose.yml`、`AgentConsole/.env.example` | — | `git check-ignore`（驗 ignore 一律用「目錄底下的檔案路徑」，記憶 `git-check-ignore-dir-pattern-false-negative`）、CI | 主控收尾單窗 | 單窗 |
| L9 | RTM 對帳（US 58）、`CLAUDE.md`／`README.md` 行數閘 | `docs/06_quality/RTM.md` | 子表先例 `RTM.md:488-492`（§2.8／§2.9 存根）；每期 `AgentConsole/docs/06_quality/RTM-ResearchToPRD-P<N>-<日期>.md` | docs 閘 | PKG-DOC | 單窗 |
| L10 | Bridge 環境表一致性：`settings.py` 檔頭 ↔ `engine-bridge/README.md` ↔ `docker-compose.yml` ↔ `.env.example` | `app/settings.py:1-54` | `README.md`、`docker/README.md` | `tests/test_health_settings.py`、`tests/test_deploy_config.py` | PKG-BR-A（compose／`.env.example` 由主控代做） | 串行 |
| L11 | 研究面「console-api 零寫入」ArchUnit 字串掃描／「Bridge 不寫 FSM-STATE」AST／「Bridge 無程式路徑呼叫核准」AST／「子行程只經 `procutil` helper」AST／能力登記（`gitops` 外無 git／gh、`fetch/` 外無網路外呼） | 各測試檔 | ADR-003 D4、D7、D16；Arch §10.4 | CI | PKG-API／PKG-BR-A | 各自包內 |
| L12 | 框架↔Bridge 契約對拍（`evidence_items.json`／review JSON／聚合公式 ↔ 框架模板範例） | Bridge `research/gates/schemas.py` | `<SDD>/docs_template/sdd/requirements/*TEMPLATE.md` | `tests/test_research_schema_parity.py`（`SDD_ROOT` 存在才跑，否則 skip 並標 TOOL-ABSENCE） | PKG-BR-C（讀 F 波成品） | F 波先、BR-C 後；夾具先行不阻塞 |

---

## 5　派工波次與並行矩陣（每包＝一個 Sonnet 開發棒，派工時明寫 `model: sonnet`；不用 `fork`；開發 agent 不 commit／push，主控驗證後 commit）

| 包 | 期 | 內容 | 依賴 | 可並行於 | 必須串行於 | 持有鎖 |
|----|----|------|------|----------|-----------|--------|
| PKG-DOC0 | W0 | W0 全部文件＋白名單句 | 主控裁決 | — | 一切實作 | L5、L9 |
| PKG-F | F | 框架側（PRD §9.1 C21、C22 與 ADR-XPLAT-017 §D7 的可改檔清單；SE-PRD 模板須以 D-20 SA-01 為骨架） | PRD 草案 | PKG-DB、PKG-BR-A、PKG-FE-A | 自身內：四份模板與兩支 agent YAML 先於 workflow 主檔與 SCG-0 條文；`FRAMEWORK_STATUS.md` 重生最後 | L6 |
| PKG-DB | P0 | V16～V18＋IT（含 `research_allowlist_entries`、`rp_no` 序列與函式） | TCS 凍結 | PKG-F、PKG-BR-A、PKG-FE-A | PKG-API | L4（前半） |
| PKG-BR-A | P0 | settings、db、outbox、layout、fsm_ops、sdd_cli 動詞、router 骨架（含 allowlist 端點）、export | TCS 凍結 | PKG-F、PKG-DB、PKG-FE-A | PKG-BR-B／C | L3、L10、L11 |
| PKG-FE-A | P0 | 路由骨架、導覽＋說明登記、Stepper、清單頁、API client（依契約型別＋mock） | 契約定稿 | PKG-F、PKG-DB、PKG-BR-A | PKG-FE-B／C | L1、L2 |
| PKG-BR-B | P0 | fetch（獨立 allowlist、釘 IP、四個解析器、內建速率下限表；V-R4、V-R9〔僅 Stack Exchange〕） | BR-A 的 settings | PKG-DB、PKG-API、PKG-FE-B | — | — |
| PKG-API | P0 | 控制器、讀配接器、FlowPolicy、SSE、BridgeHttpAdapter、`SecurityConfig` ADMIN matcher、Open API | PKG-DB 合併 | PKG-BR-B、PKG-FE-B | `schema.d.ts` 重產 → PKG-FE-B／C 的真實接線 | L4（後半）、L11 |
| PKG-BR-C | P0 | personas／playbooks／prompts、gates、orchestrator、`:approve-baseline`／`:return`（V-R1、V-R2、V-R3、V-R5） | BR-A＋BR-B＋F 波成品（夾具可先行） | PKG-API、PKG-FE-B | 整合測試 | L12 |
| PKG-FE-B | P0 | ① 面板（議題、時間軸、證據矩陣、AllowlistDialog） | FE-A、契約 | PKG-BR-B／C、PKG-API | — | —（只動 `components/domain/research/*` 與 `lib/domain/research.ts`） |
| PKG-FE-C | P0 | ② 面板（編輯器、Diff、Mermaid、雷達、核准、ESCALATION 區塊） | FE-A、`diff`／`mermaid` 相依裝妥 | PKG-FE-B（不同檔） | `package.json`／`package-lock.json` 改動串行 | —（相依檔單棒） |
| 整合 P0 | P0 | Docker E2E（mock claude）＋真機驗收＋V-R 實測 | 以上全部 | — | — | — |
| PKG-DB-P1 | P1 | V19 全部＋IT | P1 TCS 凍結 | PKG-BR-D、PKG-FE-D | PKG-API-P1 | L4 |
| PKG-BR-D | P1 | `route.py`／`scaffold.py`／`gitops.py`／`scr.py`／範本 `python-fastapi`、`tcs-draft` stage（V-R8） | BR-A、F 波 | PKG-DB-P1、PKG-FE-D | 整合 | L3（`sdd_cli.py` 的 `HUMAN_PENDING` 採納值若未在 P0 加入則由 BR-A 補） |
| PKG-API-P1 | P1 | 分流（preview／route）、SCR、拆解、`capabilities` 端點與 matcher | PKG-DB-P1 合併 | PKG-BR-D、PKG-FE-D | `schema.d.ts` 重產 | L4 |
| PKG-FE-D | P1 | `RouteDrawer`、③面板、④前半（TCS 草擬／核准）、`capabilities` UI 停用 | FE-A／B／C、契約 | PKG-BR-D、PKG-DB-P1 | — | — |
| 整合 P1 | P1 | 拋棄式 clone 與 `gh` 假替身 E2E＋掌舵者 Private 庫真機 | P1 全部 | — | — | — |
| PKG-BR-E | P2 | `release.py`、`:gates`／`:tag`／`:pr` | P1 RELEASE | PKG-FE-E | 整合 | L3 |
| PKG-API-P2 | P2 | 交付與 SCG 登錄端點、matcher | PKG-BR-E | PKG-FE-E | `schema.d.ts` 重產 | L4 |
| PKG-FE-E | P2 | `BuildPanel`、`DeliverPanel`、`ResearchBackLink`、SCR 發起鈕與橫幅、`NotificationBell` 納入 | 契約 | PKG-BR-E | — | — |
| 整合 P2 | P2 | 內環走完到交付（暫存專案）、tag 以暫存 git 驗 | P2 全部 | — | — | — |
| QA | 每期 | SCG-4 獨立審查（唯讀；全程不派背景長任務；審查期間主控不動工作樹） | 整合綠 | — | RELEASE | — |
| 收尾 | 每期 | RTM 回填、`RELEASE` 轉態、L7／L8 根層連動（若有） | QA PASS | — | — | L7、L8 |

**互踩防線**：①同一持有面只給一棒；②`package.json`／`package-lock.json`、`schema.d.ts`、`OpenApiIT` 計數是共享單點，只給單棒、其餘棒回報需求；③hooks-ON 視窗在非草擬態會依「路徑子字串」擋 `docs/01_requirements|02_architecture|03_testing/` 的 Write／Edit（BRIDGE §8.3:467-470）——**實作期間的文件編修一律走 hooks-OFF 視窗**（W0 的文件在草擬態可寫）；④派工前現查 `python tools/session_resume_planner.py --pace` 決定可同時派幾棒（值是 (水位, 距 reset) 的函式，不得記住舊值）；⑤並行包各自在**獨立 worktree**（`isolation: worktree` 看不到未 commit 修改，記憶 `worktree-isolation-uncommitted-blind-spot`：派前先本機 commit）或確定檔案互斥；⑥Windows 的 `git worktree remove` 前先單獨刪除 `node_modules` junction（記憶：worktree 收場先刪 junction）。

---

## 6　hooks-ON 視窗啟動（沿 BRIDGE §8.1:367-393；從 monorepo 根的 PowerShell／bash 視窗啟動）

```powershell
$root = (Get-Location).Path
$ver  = ((python AISDLC_SDD/scripts/sdd_version.py) -replace '^AISDLC_SDD_v', '').Trim()
$sub  = 'agentconsole'; $slug = 'research-to-prd-p0'      # 框架窗：$sub='sdd'; $slug='research-to-prd'；P1／P2 換 slug
$rel  = @{ autoclaude='AutoClaude\build\reports\fsm'; agentconsole='AgentConsole\build\reports\fsm'; monorepo='build\reports\fsm'; sdd="AISDLC_SDD\AISDLC_SDD_v$ver\build\reports\sdd-dogfood" }
$env:SDD_ACTIVE_VERSION = $ver; $env:SDD_PROJECT = "$sub-$slug"; $env:SDD_STATE_DIR = Join-Path $root $rel[$sub]
$env:SDD_ENABLE_RULE_FIRE_TELEMETRY = '0'; $env:SDD_ENABLE_RULE_CATCH_TELEMETRY = '0'
# 先做 BRIDGE §8.2 (a)(c) 的三件組同址與活性驗收，通過才 claude
```
```bash
root="$(git rev-parse --show-toplevel)"; ver="$(python AISDLC_SDD/scripts/sdd_version.py | sed 's/^AISDLC_SDD_v//')"
sub=agentconsole; slug=research-to-prd-p0   # 框架窗：sub=sdd slug=research-to-prd；P1／P2 換 slug
case "$sub" in autoclaude) rel=AutoClaude/build/reports/fsm;; agentconsole) rel=AgentConsole/build/reports/fsm;; monorepo) rel=build/reports/fsm;; sdd) rel="AISDLC_SDD/AISDLC_SDD_v$ver/build/reports/sdd-dogfood";; esac
export SDD_ACTIVE_VERSION="$ver" SDD_PROJECT="$sub-$slug" SDD_STATE_DIR="$root/$rel" SDD_ENABLE_RULE_FIRE_TELEMETRY=0 SDD_ENABLE_RULE_CATCH_TELEMETRY=0
# 先做 BRIDGE §8.2 (a)(c) 的三件組同址與活性驗收，通過才 claude
```
Stage-1 基線採納文件（agentconsole；BRIDGE §8.4:511）：`docs/01_requirements/Agent_ConsoleUI_PRD.md`、`AgentConsole/docs/02_architecture/{Architecture,ADR-001-TechStack-Lock,ADR-002-Frontend-Design-System,API_Contract_P3-6}.md`、`openapi-p3-6.yaml`，本功能另加 `ResearchToPRD_PRD.md`、`API_Contract_ResearchToPRD.md`、`ADR-003-ResearchToPRD.md`（`--root` 取 monorepo 根）。`--approver`＝凍結常態規則的主控代理字樣（根 `CLAUDE.md`〈派工模型與凍結常態規則〉；需該階段獨立審查 PASS 且親驗無 P1／P2）；**這是開發本功能的 `spec-frozen`，與產品內 Gate 0 永遠要求真人點擊是兩回事（D-19）**。

---

## 7　V 驗證項的歸屬（每項由哪一棒在哪一期落證據）

| ID | 點 | 歸屬 | 期 |
|----|----|------|----|
| V-R1 | headless `--allowedTools`／`WebFetch(domain:…)` 語法與無提示行為 | PKG-BR-C 開發棒（真機本機模式） | P0 |
| V-R2 | **負向**：repo 外工作區不載入根 CLAUDE.md 鏈／根 hooks、每回合 token（D-28） | PKG-BR-C＋主控 | P0（量測閘） |
| V-R3 | `-p <prompt>` 命令列長度與 `.prompts/` 參照法 | PKG-BR-C | P0 |
| V-R4 | httpx 釘 IP＋SNI（不可行則退回解析後比對 IP 非私網） | PKG-BR-B | P0 |
| V-R5 | 無 `MINIMAX_API_KEY` 時 evaluator 失敗後的重試行為 | PKG-BR-C（mock claude 夾具） | P0 |
| V-R6／V-R7 | FSM 首次 `show` 建檔、第 3 次 FAIL 後現態；`spec-frozen --digest --root <工作區>` | PKG-BR-A（暫存狀態目錄；腳本見附錄 A） | P0 |
| V-R8 | Bridge 環境下 `gh auth status`／`GH_TOKEN` | P1 的 route 棒（PKG-BR-D） | P1 |
| V-R9（新增，D-17；主控已現查，殘餘僅 Stack Exchange） | 各來源官方速率限制數值：**主控已現查 arXiv、GitHub（含搜尋端點）、Semantic Scholar**，PRD NFR-R2P-03-6 已回填（出處 §9.0 Q19）；**Stack Exchange 官方頁當時無法抓取，由 PKG-BR-B 以官方文件補證**，回填 PRD NFR-R2P-03-6 與 allowlist 條目 `min_interval_seconds` | PKG-BR-B | P0 |

---

## 8　可重啟點（根 `CLAUDE.md`〈可重啟點四條件〉；以下是 2026-11-02 寫稿當下的快照，落檔 commit 之後一律以 git 現況為準）

- **已驗證什麼**：寫稿當下對 repo 唯讀（HEAD＝`01d9be6e`）、未跑任何 FSM 寫入動詞。讀檔核對的事實（皆附座標）：導覽登記表現況九列、`mobile:true` 6 列、`order` 10／20／30（停用）／40／50／55／70／75／80（`AgentConsole/frontend/lib/nav/registry.ts:42-115`）；`SecurityConfig` 的 ADMIN 規則先例與通用規則位置（`AgentConsole/backend/src/main/java/com/aisdlc/console/infrastructure/config/SecurityConfig.java:86-99`）；Architecture 各錨點（`Architecture.md` §2.2、§3、§5.1、§5.4、§6、§7.2、§8.2～8.4、§9.4、§10.1～10.3、§11.1～11.3、§12.1～12.2）；Console PRD §0.7／§0.8／§8.1 錨點（`Agent_ConsoleUI_PRD.md:124-147,1880-1914`）。**未驗證**：V-R1～V-R9 全部（其中速率限制官方數值已由主控現查回填 PRD NFR-R2P-03-6，僅 Stack Exchange 未現查）、DDL 在真 PG 的套用。
- **還沒做什麼**：本文件集尚未落檔進 repo；SCG-0 獨立審查未跑；主控尚未做的根層連動（`.gitignore`、CI `paths`、compose／`.env.example`、`AgentConsole/CLAUDE.md` 鐵律 7 句、ADR-XPLAT-016 回寫、Implementation_Plan 進度帳列）；框架側 TCS／agent／模板（框架鍵 `sdd-research-to-prd` 的視窗範圍；**不產生框架側 PRD**，D-41）；P0 TCS。
- **下一步的確切指令**：①`git -C $root rev-parse --short HEAD`（應為 `01d9be6e` 或其後代）與 `git -C $root status --short`，重驗落檔前基線；②依本檔 §2 W0 表與 PRD §9.0〈模組落點表〉的路徑把文件集落進 repo（Architecture 與 Console PRD 兩檔是增補併入既有檔、其餘為新檔），落檔後對每個新檔與兩個被增補檔以 `Get-FileHash -Algorithm SHA256` 記 sha256 入證據檔；③派 QA 做 SCG-0 獨立審查（`model: sonnet`、唯讀、報告落 `docs/06_quality/SCG0-REVIEW-ResearchToPRD-<YYYYMMDD>.md`）；④主控親驗無 P1／P2 後，開鍵 `agentconsole-research-to-prd-p0`（§6 啟動腳本＋BRIDGE §8.2 (a) `show` 建檔），Stage-1 採納（§6 的文件表）、Stage-2 TCS 凍結。
- **禁止事項**：不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS`、不准 `git stash`（除 `stash create`）、不准 `git checkout --`；不改 `_HAPPY_PATH`／`formal/`；IMPLEMENTATION 態不寫 `docs/01～03`；不代跑 ESCALATION 恢復；子代理一律 `model: sonnet`、不用 `fork`；AgentConsole 三鍵的開發棒不得動框架樹與根層檔；不得把速率限制的保守初值寫成已驗證事實。
- **重啟後第一件事＝重驗**：不採信本節任何「已驗證」宣稱（zero-trust 雙向，對自己上一段的宣稱亦然）。

---

## 附錄 A　V-R6／V-R7 暫存狀態目錄實跑腳本（PowerShell 與 bash 並列；供 PKG-BR-A／QA 在**暫存**狀態目錄實跑，不碰 AutoClaude／AgentConsole／框架樹的狀態目錄）

```powershell
$root = (git rev-parse --show-toplevel)
$ver  = ((python AISDLC_SDD/scripts/sdd_version.py) -replace '^AISDLC_SDD_v', '').Trim()
$vd   = Join-Path $root "AISDLC_SDD\AISDLC_SDD_v$ver"; $py = Join-Path $root '.venv\Scripts\python.exe'
$tmp  = Join-Path $env:TEMP ("rtp_fsm_probe_" + [guid]::NewGuid().ToString('N').Substring(0,8))
$sd   = Join-Path $tmp 'build\reports\fsm'; New-Item -ItemType Directory -Force $sd | Out-Null
$env:SDD_STATE_DIR = $sd; $env:SDD_PROJECT = 'research-probe'
$env:SDD_ENABLE_RULE_FIRE_TELEMETRY = '0'; $env:SDD_ENABLE_RULE_CATCH_TELEMETRY = '0'; $env:SDD_ENABLE_AUTO_RECOVERY = '0'
function sdd { & $py -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime @args }
Push-Location $vd -ErrorAction Stop
$null = sdd show --project research-probe                                    # V-R6：不帶 --must-exist＝建檔
foreach ($to in 'SCENARIO_DETECT','AGENT_LOAD','SPEC_DRAFTING','SCG_VALIDATION') {
    sdd transition --project research-probe --must-exist --to $to --reason 'probe' --trigger research_bridge
}
1..3 | ForEach-Object { sdd gate --project research-probe --must-exist --gate SCG_VALIDATION --result FAIL --reason "probe round $_" }
$final = sdd show --project research-probe --must-exist                       # 預期：第 3 次輸出含 "escalated": true；現態 ESCALATION，且不是 AUTO_RECOVERY_ATTEMPT／ESCALATION_FINAL
Pop-Location
Remove-Item Env:SDD_STATE_DIR, Env:SDD_PROJECT, Env:SDD_ENABLE_AUTO_RECOVERY
# 收尾：Remove-Item -Recurse -Force $tmp（只刪本探針自建的暫存目錄）
```
```bash
root="$(git rev-parse --show-toplevel)"; py="$root/.venv/bin/python"
ver="$(python AISDLC_SDD/scripts/sdd_version.py | sed 's/^AISDLC_SDD_v//')"; vd="$root/AISDLC_SDD/AISDLC_SDD_v$ver"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/rtp_fsm_probe_XXXXXXXX")"; sd="$tmp/build/reports/fsm"; mkdir -p "$sd"
export SDD_STATE_DIR="$sd" SDD_PROJECT=research-probe SDD_ENABLE_RULE_FIRE_TELEMETRY=0 SDD_ENABLE_RULE_CATCH_TELEMETRY=0 SDD_ENABLE_AUTO_RECOVERY=0
sdd() { "$py" -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime "$@"; }
(
  cd "$vd" || exit 1
  sdd show --project research-probe > /dev/null                                  # V-R6：不帶 --must-exist＝建檔
  for to in SCENARIO_DETECT AGENT_LOAD SPEC_DRAFTING SCG_VALIDATION; do
    sdd transition --project research-probe --must-exist --to "$to" --reason probe --trigger research_bridge
  done
  for i in 1 2 3; do sdd gate --project research-probe --must-exist --gate SCG_VALIDATION --result FAIL --reason "probe round $i"; done
  sdd show --project research-probe --must-exist                                 # 預期同 PowerShell 形態
)
unset SDD_STATE_DIR SDD_PROJECT SDD_ENABLE_AUTO_RECOVERY
# 收尾：rm -rf "$tmp"（只刪本探針自建的暫存目錄）
```
預期對照：前兩次 FAIL `next_state=SPEC_DRAFTING`、第三次 `escalated:true`，`retry_count` 依序 1／2／3（HUMAN_PENDING 下的兩個負控——`gate SCG_VALIDATION FAIL` 態不動且計數＋1、`gate SCG_VALIDATION PASS` rc≠0——依 D-50 由 P0 TCS 附腳本，形態同上；ESCALATION 人工恢復後的預算負控——3 次 FAIL→`resume-from-escalation --to SPEC_DRAFTING`〔腳本直接呼叫框架 CLI，Bridge 不呼叫〕→`current_count` 仍為 3，再一次 FAIL 立即再 ESCALATION、改 PASS 則歸 0——依 D-60 由 P0 TCS 附腳本）；PASS 路徑 `retry_history.SCG_VALIDATION.current_count` 歸 0；`spec-frozen --stage Gate-0 --digest --root <暫存根> --doc …` 的 `frozen_stages[-1].spec_doc_digests`（V-R7）。

## 附錄 B　`Implementation_Plan.md` §5.1 進度帳增列文字（表頭 `:432`＝波次｜狀態｜commit｜出口閘門結果｜未結缺陷｜備註；先例列 `:434`、較新的「補列」體例 `:446-448`；接在表尾，表尾位置落檔時現查）

```
| RTP-W0（ResearchToPRD 規格波） | 🟡 進行中 | 待主控 | 文件集已合成（PRD、ADR-003、ADR-XPLAT-017、API 契約、Architecture 增補、Console PRD §0.9、本計畫書）；SCG-0 一審 FAIL 已依 D-60～D-64 修訂；二審 FAIL（P2 1）已依 D-65 修訂；三審 PASS（P3 1）已依 D-66 補記；待主控凍結；主控裁決 D-12～D-66 | 無 | Stack Exchange 速率限制官方數值未現查（V-R9 殘餘；其餘三來源已現查回填）；框架側文件由框架鍵視窗另行產出 |
```
（P0／P1／P2 各期完成時以同格式增列，證據欄逐字貼 §3 出口閘的 rc 與 AT 輸出。）
