# Test Contract Specification — ResearchToPRD P1（分流精靈與軌道 A／B、SDD 內環鍵採納、TCS 草擬與任務拆解交棒、SCR 後端；DB V19、Bridge 分流與 SCR 與拆解橋、console-api P1 端點、frontend 步驟 3 與步驟 4 前半）
# 測試契約規格文件（增量變更；FRD-lite 併入檔頭）

**文件類型**: Test Contract Specification (TCS)
**SDD Gate**: SCG-4 PR Review Gate（RG-TEST 為補充閘）
**使用時機**: 已凍結系統（AgentConsole 前端導覽登記表與說明登記表、console-api、Engine Bridge；上位文件含 Console PRD §0.9、Architecture、ADR-001、ADR-002、ADR-003、ADR-XPLAT-017、API 契約兩份、ResearchToPRD PRD）的單一 Feature 的 P1 期（P0 已 RELEASE）；FRD-lite 與 TCS 同檔
**存放位置**: `AgentConsole/docs/03_testing/contracts/TCS-ResearchToPRD-P1-20261107.md`（相對 monorepo 根；`spec-frozen --root` 取 monorepo 根，因上位文件含根層 PRD 與根層 ADR）
**spec-format-version**: 1.0
**scenario**: brownfield

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **Feature ID** | F-907 |
| **Feature 名稱** | ResearchToPRD P1：Gate 0 之後的分流與交棒——分流精靈（預演零副作用、僅 ADMIN 確認）、軌道 A（獨立 worktree 併入既有模組）、軌道 B（登記制範本、複製研究工作區、git 與 gh）、內環鍵建立與 Stage-1 基線採納、任務拆解（覆蓋對映、簽核）、TCS 草擬（tcs-draft）、規格變更請求 SCR 的後端與 FSM 序列；Flyway V19；步驟 3 真面板與步驟 4 前半取代占位 |
| **User Story** | US-923（分流與軌道，對應 PRD 的 US-R2P-11、12、13）、US-924（SDD 綁定、拆解交棒與 TCS 草擬，對應 US-R2P-14）、US-925（SCR 後端與橫切增量，對應 US-R2P-19 的後端部分與 US-R2P-21、22、23 的 P1 增量）；SD 已以 Grep 對 `AgentConsole/docs`、`docs`、`AgentConsole`（排除 node_modules）確認 F-907、US-923、US-924、US-925、AC-961 皆未被使用，不撞號（指令與結果見交卷自查檔） |
| **建立日期** | 2026-11-07 |
| **輸入快照** | HEAD＝`9c628f0f`；上位檔 digest 見〈增量追溯表〉（主控落檔時以 `Get-FileHash -Algorithm SHA256` 對工作樹逐檔現算；Stage-1 凍結由 CLI 重算為準） |
| **QA 負責人** | 本鍵 SCG-4 QA 棒（獨立審查者；規格作者＝SD 棒，實作者＝鍵 `agentconsole-research-to-prd-p1` 的各包開發 agent，三方不同） |
| **FSM 功能鍵** | `agentconsole-research-to-prd-p1`（一律從 monorepo 根啟動；`python AISDLC_SDD/scripts/sdd_env.py --sub agentconsole --slug research-to-prd-p1`） |
| **SCG Gate** | SCG-4 □ 待審 |

---
## 增量變更專用：FRD-lite 與〈增量追溯表〉

> 適用 `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`〈增量（delta）條款〉：變更限於已凍結系統的單一 Feature 的 P1 期。**凍結檔不得再改**：上位 TCS（含 TCS-P0）的訂正只寫在各自〈勘誤〉表（本檔 §4.4 列出需勘誤者及座標），走 refreeze；本檔為使其可測而補定義者標「本檔類推」並列入 §7。**本檔只管 P1**：PRD 內屬 P2 的 AC 列於 §1.3，由 `agentconsole-research-to-prd-p2` 的 TCS 承接；P0 已落地者不重做。**框架側（`AISDLC_SDD`）本鍵零改動**（框架鍵 `sdd-research-to-prd` 已 RELEASE；本鍵對框架 agent 與模板的讀取以夾具為準，整合 P1 以框架成品對拍）。本檔依主控裁決 D-87～D-125（`S\HELM_DECISIONS_P1.md`；與規格字面衝突時以裁決為準並標「依 D-NN」）與 Architect＋SA 棒的接口定稿（IFACE 第二版）與分包（PACKAGES 第二版）撰寫。

### FRD-lite

**背景（掌舵者 2026-11-07 指令「確認 ResearchToPRD_PRD.md 與來源規格功能都已經完成實作與 E to E 測試機制」）**：P0（外環：研究工作區、PRD 工作室、Gate 0）已 RELEASE；P1 補上 Gate 0 之後的分流與交棒。PRD 全文 `docs/01_requirements/ResearchToPRD_PRD.md`（FR-R2P 23、AC-R2P 171）；決策 ADR-003（D1～D16）、ADR-XPLAT-017（D1～D7）；契約 `API_Contract_ResearchToPRD.md` v1.0（含勘誤）；DDL 全文 Architecture K.4；計畫書 `ResearchToPRD_Plan.md` §5；主控裁決 D-87～D-117。

**現況與變更（Before／After；brownfield）**

- Before：(1) Flyway 最大號 V18，沒有 `research_route_decisions`、`research_route_steps`、`research_scr`、`research_decompositions`、`research_deliveries` 與視圖 `v_research_healing_attempts`；(2) Bridge 沒有分流、scaffold、gitops、SCR、拆解橋；`routers/research.py` 的 `tcs-draft` 回 501 `not_implemented`；`GET /research/capabilities` 的 `scaffold_root` 恆為 null、`scaffold_templates` 恆為空、`repo_writable` 讀 `REPO_ROOT`、`gh_cli.authenticated` 為 `NOT-EVALUABLE`；`gates/reconcile.py` 的 `route_decision`、`task_decomposition` 兩項兩側皆缺席判 ok；`sdd_cli.py` 的 `transition --to HUMAN_PENDING` 只准 `baseline adoption` 理由前綴；能力登記鎖禁止研究面出現 git 與 gh 子行程；(3) console-api 沒有分流、SCR、拆解端點，`OpenApiIT` 為 101 條路徑與 115 個操作，`SecurityConfig` 的 `route` ADMIN 規則已預置而 `scr` 與 `decomposition` 無規則；`ResearchReasonsTest` 鎖 22 個 reason；既有 execute 與 resume 啟動服務沒有研究專案前置守衛；(4) frontend 步驟 3 至 5 為占位面板（`research-placeholder`），`lib/api/endpoints.test.ts` 釘 109 個端點函式。
- After：(1) 新增 `V19__research_route_scr_delivery.sql`（DDL 全文取 Architecture K.4，不得自改；**P1 不需 V20**，D-116）；(2) Bridge 新增 `app/research/{route,scaffold,gitops,scr,decompose_plan}.py`、`app/routers/research_route.py`、`research_scr.py`、`scaffold_templates/python-fastapi/`；新端點 `:route-preview`、`:route`（同步，牆鐘 300 秒；D-105）、`:route-compensated`、`:decompose`、`:decomposition-signoff`、`:scr`、`:scr-apply`；`stages/tcs-draft:start` 取代 501；`sdd_cli.py` 新增第二個理由前綴 `tcs gate`（D-97；動詞集合不變）；`gitops.py` 為 git 與 gh 子行程唯一出口（D-99）；對帳兩項取真比對；capabilities 十三鍵不變、`scaffold_root`、`scaffold_templates`、`repo_writable` 取實值；(3) console-api 新增 `POST …/route/preview`、`…/route`、`GET …/route`、`POST …/scr`、`GET …/scr`、`POST …/scr/{scrNo}/apply`、`GET …/decomposition`、`POST …/decomposition`、`POST …/decomposition/signoff` 共九個操作與六條路徑（`OpenApiIT` 107／124，算法見 AT-961-15-3）、先建 `projects` 列再呼 Bridge 與失敗補償、執行前置守衛（D-102）、九個新 reason（P0 的 22 個加 P0 尾巴 4 個加 P1 的 9 個）；(4) frontend 新增 `RoutePanel`、`RouteDrawer` 等步驟 3 元件與 `BuildFrontPanel` 等步驟 4 前半元件、`ResearchWorkspaceView` 的 route 與 build 兩步接真面板（deliver 仍占位）、三個衍生相態標籤、說明登記表第 3、4 步寫實內容。
- **非目標**：P2 全部（看板五階段、自癒監視器、終端窗格、人機協同彈窗其餘類型、SCR 發起鈕與橫幅、交付與歸檔、`ResearchBackLink`、`:gates`／`:tag`／`:pr`）；P0 已落地者不重做；不動 `_HAPPY_PATH`、`formal/`、`R-*.yaml`；不新增 hook、守衛碼、根層 `tools/` 模組；不新增 `os.replace`、`rename`、`move` 站點；不新增前端相依（`package.json` 不動）；不改既有 `:freeze` 契約；研究範圍修訂端點延後（D-115）；node 與 java 範本不在 P1。

**AC 編號規則**

1. **編譯文法**：AC 為 `AC-[\d\-]+`、AT 為 `AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*` 且 AT 前兩段數字＝所屬 AC（ADR-XPLAT-016 §8.1）。PRD 的 `AC-R2P-NN-Y` 含字母，故本檔沿 P0 採**雙名**：機器可讀位置（§1.5、§3）一律用 `AC-961-n`；人讀處一律同時寫出 PRD 全名。
2. **對映**：本檔 AC 家族號 961（現有最大號為 960，不撞號），共 25 個 AC。AC-961-n 是**契約級**條款，比 AC-R2P 粗；PRD 內屬 P1 的 37 條 AC-R2P（FR-R2P-11～14 與 19 後端）加 10 條增量半條，全數映到至少一個 AC-961 與其 AT（對照全表在 §1.2）；PRD 內屬 P2 的 23 條列於 §1.3。
3. **AT 命名**：`AT-961-<AC 序>-<序>`；負控與邊界 `AT-961-<AC 序>-E-<序>`；測試名含其底線形（`AT-961-3-2`→`AT_961_3_2`；Java 方法名以底線形開頭、後接駝峰敘述；pytest 函式名為 `test_AT_961_3_2_…`；vitest 的 `it` 標題以底線形開頭）。每個 AC 內數字序與 E 序各不超過 9。
4. **計數**：AC 25 個、AT 210 個（正控 166、負控與邊界 44）；另有 V 系列（§6.2，不是 AT）。RTM 子表列數＝F 1＋US 3＋AC 25＋AT 210。（RELEASE_READY 勘誤批次新增 AT-961-12-E-2：209→210、43→44、列數 238→239；見〈勘誤〉表 E-15）

**User Story**

| US | 對應 PRD | 敘述 | 涵蓋 AC |
|----|----------|------|---------|
| US-923 | US-R2P-11、12、13 | 作為掌舵者，我要在 Gate 0 核准後用預演確認「按下去會發生什麼」，再由 ADMIN 確認分流；軌道 A 在獨立 worktree 併入既有模組且不干擾我正在用的工作樹，軌道 B 一次完成新專案骨架、CI、compose 與 GitHub 初始化且絕不洩漏機密 | AC-961-2、3、4、5、6、8、14、16、17 |
| US-924 | US-R2P-14 | 作為掌舵者，我要把核准的 PRD 以內環鍵採納為基線、草擬測試規格、自動拆成帶「覆蓋哪些 AC」的任務草稿，並在我簽核前不准執行 | AC-961-7、9、10、11、18、19、25 |
| US-925 | US-R2P-19（後端）、US-R2P-21、22、23 的 P1 增量 | 作為 OPERATOR，我要在發現規格有瑕疵時走正式的變更請求退回外環；作為掌舵者，我要資料表、對帳、稽核與說明在 P1 一併到位且守衛不鬆動 | AC-961-1、12、13、15、19、20、21、22、23、24 |

**本增量交付物**（D1～D9；路徑相對 monorepo 根；每包一個 Sonnet 開發棒，派工明寫 `model: sonnet`；各包的「允許變更檔案集合」見 §5.7；依 D-114 七包三波）

| 編號 | 交付物 | 路徑 | 製作者 | 主要驗證 |
|------|--------|------|--------|----------|
| D1 | V19 與 IT | `AgentConsole/backend/src/main/resources/db/migration/V19__research_route_scr_delivery.sql`（DDL 取 K.4）；`ResearchSchemaMigrationIT` 擴充；五個既有 Flyway IT 的版本清單；`BackupJobMigrationIT.snapshotOfExistingTables`；`engine-bridge/tests/research_pg_support.py` | PKG-DB-P1 | AC-961-1 |
| D2 | Bridge 分流 | `app/research/{route,scaffold,gitops,adopt}.py`（`adopt.adopt_baseline`＝基線採納，D-126）、`app/routers/research_route.py`、`scaffold_templates/python-fastapi/**`、`app/research/settings.py` 與 `app/settings.py`（`BRIDGE_SCAFFOLD_ROOT`、`BRIDGE_WORKTREE_ROOT`、`BRIDGE_REPO_ROOT`、`BRIDGE_ROUTE_TIMEOUT_SECONDS`）、`db.py` 與 `outbox.py` 的分流 Op、能力登記與 AST 鎖測試 | PKG-BR-D1 | AC-961-2～8、16、20（route 側） |
| D3 | Bridge SCR、TCS 草擬、拆解橋 | `:reconcile` 的 `TCS_PENDING × Stage-2 已凍結` 校正（D-125）；`app/research/{scr,decompose_plan}.py`、`app/routers/research_scr.py`、`routers/research.py`（移除 tcs-draft 501、approve-baseline 的 open-SCR 分支）、`orchestrator.py` 與 `gates/reconcile.py`（兩項對帳）、`compile/*`（spec-engineer）、`sdd_cli.py`（`tcs gate` 前綴）、`export.py`（版本號規則） | PKG-BR-D2 | AC-961-9、10、12、13、20 |
| D4 | console-api | `FsmView.stage2Frozen`、`ResearchFlowPolicy` 讀端衍生、SDD freeze 成功後呼 Bridge `:reconcile`（D-125）；分流、SCR、拆解的 DTO、讀配接器、服務與端點；`SecurityConfig`（`scr/*/apply` ADMIN）；`ErrorReasons` 與 `ResearchErrorDocs`；`ResearchFlowPolicy`；執行前置守衛；設定鍵 `research.github_token`；`BridgeHttpAdapter` 逾時表；`OpenApiIT`、`RbacIT`、`ResearchReasonsTest` | PKG-API-P1 | AC-961-11、14、15、16（DTO）、21 |
| D5 | frontend 步驟 3 | `RoutePanel`、`RouteDrawer`、`RouteCardA`、`RouteCardB`、`RouteActionList`、`RouteStepsTimeline`、`PublicRepoConfirm`；`ResearchWorkspaceView` 接線；`lib/domain/research.ts`、`lib/api/*`、`reasons.ts`、說明登記表 | PKG-FE-D1 | AC-961-16（UI）、17、19 |
| D6 | frontend 步驟 4 前半 | 「重新對帳」鈕（D-125）、`BuildFrontPanel`、`TcsCard`、`DecompositionCard`、`CoverageList`、`WaiverInput`、`InnerLoopLinks`、`ScrStateBadge` | PKG-FE-D2 | AC-961-18 |
| D7 | 接線 | `lib/api/schema.d.ts` 重產、`types.ts` 改引生成型、真棧 spec 與 helper 合併 | PKG-FE-W | AC-961-19（型別）、22（真棧） |
| D8 | 整合 P1 | `engine-bridge/tests/test_research_int_p1.py`、`tests/e2e/research-p1-docker.stack.spec.ts`、假 gh 夾具、Docker 與本機模式實跑、V 系列證據 | 整合棒或主控 | AC-961-22 |
| D9 | 文件連動（主控） | Architecture 與契約與 ADR 勘誤批次、RTM 回填與 `RTM.md` §2.10 補述、Implementation_Plan 進度帳一列、SCG-4 報告；根層連動（CI paths 等）由主控代做 | 主控 | AC-961-23、24 |

**提交順序與責任**

- 依 PACKAGES 第二版：波 1＝PKG-DB-P1 ∥ PKG-BR-D1 ∥ PKG-FE-D1；波 2＝PKG-BR-D2（BR-D1 合併後）∥ PKG-API-P1（DB-P1 合併後）∥ PKG-FE-D2（FE-D1 合併後）；波 3＝PKG-FE-W（API-P1 合併後，重產 `schema.d.ts`）；之後整合 P1、SCG-4 QA 鏡、修復棒、RTM 回填。每支程式完成立即編譯並跑該區 AT（`AgentConsole/CLAUDE.md` 鐵律 11），不累積。
- 開發 agent **不准 commit／push**（鐵律 3）；不動 §5.7 各包集合以外的檔（鐵律 7）；根層檔與框架樹需要變動時回報主控；真帳本、真 `~/.autosdd/`、真 `AgentConsole/build/reports/fsm`、真 repo 一律唯讀（FSM 實跑只在暫存狀態目錄；真 git 只在 `$env:TEMP` 拋棄式 clone；`gh` 一律假可執行檔夾具）。
- DB 型 Bridge AT 需要 `BRIDGE_TEST_DSN` 指向可建庫的 PostgreSQL；框架對拍與真 CLI 型 AT 需要 `SDD_ROOT`。**SCG-4 與 RTM 證據一律在兩者皆在場下跑到 0 skipped**；缺任一者造成的 skip 不得當作通過（§2 的 TOOL-ABSENCE 規則）。
- **FIX 包允許集合**（P0 未結 R-4 的寫法承接）：修復棒的允許集合＝原包集合∪該審查報告指名的檔；報告未指名的檔一律回報主控，不得自行擴張。

**〈增量行為規則〉**（W-P1～W-P23；各 AT 與 §1 以 W-P 編號引用。實查依據：PRD §5、§8.1；ADR-003 D1～D16；ADR-XPLAT-017；契約 §0～§5；Architecture K.4；IFACE 與 PACKAGES 第二版；`engine-bridge/app/{sdd_cli,settings,fsutil,mock_claude,procutil,security}.py`、`routers/{research,sdd}.py`；backend 的 `SecurityConfig`、`OpenApiIT`、`RbacIT`、`ResearchReasonsTest`；frontend 的 `lib/domain/research.ts`、`lib/help/*`、`ResearchWorkspaceView`）

- **W-P1 Bridge 仍是研究表唯一寫入者**：console-api 對 V19 五表零寫入（ArchUnit 字串掃描）；console-api 只寫自己的 `projects` 列與 `audit_log`；`COMPENSATED`、`SIGNED_OFF`、`import_record_id` 一律由 Bridge 依 console-api 的通知寫入（D-112、D-113）。
- **W-P2 fail-loud、不降級、DB 先於副作用**：無 DSN 時沿 P0 回 503；分流每步先寫 `RUNNING` 列再執行副作用；寫入器不吞錯；預演零副作用（D-108：所有 `research_*` 表與 `projects` 零變化，`audit_log` 一列橫切不計）。
- **W-P3 git 與 gh 單一出口**：`research/gitops.py` 是 git 與 gh 子行程的唯一出口（ADR-003 D16 與 D-99）：argv 陣列、`shell=False`、環境白名單重建、經 `popen_platform_kwargs()`；禁止形態（強推、硬重設、clean、stash、檢出路徑、restore 路徑、switch -f、全域與系統 config）一律在 spawn 前拒絕；使用者片段先過列舉或正規式。
- **W-P4 分流狀態**：路由列 `PENDING→RUNNING→SUCCEEDED｜FAILED`，`FAILED→RUNNING`（重試，同列）、`FAILED→COMPENSATED`（補償通知）；每研究專案至多一個 PENDING／RUNNING／SUCCEEDED（部分唯一索引）；成功才寫 `02_governance/route_decision.json` 並推進游標到 `build`／`ROUTED`／`IDLE`；執行中為 `route`／`ROUTING`／`RUNNING`，失敗為 `route`／`ROUTING`／`FAILED` 且 `flow_detail` 為失敗步驟名（D-105）；`:route` 為同步 HTTP（200 或 502 `route_step_failed`），牆鐘上限 300 秒。
- **W-P5 軌道 A**：獨立 worktree（`git -c core.longpaths=true worktree add -b <branch> <path> <base_ref>`，根為 `BRIDGE_WORKTREE_ROOT`，D-95）、不切換使用中工作樹、不 stash、不 clean、不 `add -A`（只 `add -- <明列路徑>`）、不改治理檔；分支變更限 PRD 發佈檔與落點 stub（D-101）。
- **W-P6 軌道 B 與容器模式**：`BRIDGE_SCAFFOLD_ROOT` 無預設（未設＝軌道 B 停用）；範本登記制（目錄清單；P1 僅 `python-fastapi`）；複製→逐檔驗證→原地保留；容器模式（無 gh、無可寫 repo）不支援真分流（D-29、D-96）；`BRIDGE_REPO_ROOT` 覆寫 `repo_writable` 的判斷根。
- **W-P7 token 與可見性**：預設 Private；Public 須輸入庫名確認；GitHub token 取自後端設定鍵 `research.github_token`（加密、預設空），只在 `route` 且 `createGithub=true` 時放進單次請求本文，Bridge 只經子行程環境 `GH_TOKEN` 傳 gh，不入 argv、檔案、日誌、DB、回應（D-98）；初始 commit 排除 `00_research/raw/**` 與 `.env`。
- **W-P8 內環鍵與 Stage**：Bridge 於目標根建內環鍵並採納基線（`show`＋5 次 `transition`＋`spec-frozen --stage Stage-1`）；Stage-2 TCS 走 `transition`（SPEC_DRAFTING→SCG_VALIDATION→HUMAN_PENDING，後者理由前綴 `tcs gate`，D-97），凍結走既有 `:freeze`；內環鍵沿既有行為（不強制關閉自動恢復）；外環鍵在分流後不被改動。
- **W-P9 FSM 單一寫入面不破壞**（基線採納住 `app/research/adopt.py`，AST 鎖 C2 白名單限該檔、內環鍵與 `--stage Stage-1`，D-126）：`RESEARCH_VERBS` 集合不變（`show`、`transition`、`gate`、`spec-frozen`、`spec-refreeze`）；`resume-from-escalation` 不入白名單；新模組先登記能力表；新模組不含 `tools.fsm_runtime` 與 FSM 動詞字面值。
- **W-P10 不新增守衛與目錄項原語**：不新增 hook、守衛碼、根層 `tools/`；不新增 `os.replace`、`rename`、`move` 站點；新 Python 檔 `open`、`read_text`、`write_text` 帶 `encoding="utf-8"`、時間戳帶時區（沿 W-R10）；範本內的 Python 檔以 `.tmpl` 後綴存放（⚖P1-18）。
- **W-P11 拆解**：planner 只產草稿（`signed_off` 為假）；`:decompose` 為同步 HTTP、非 stage run，逐 US 呼叫既有拆解服務，`covers_ac` 由該次呼叫綁定的 AC 清單確定性賦值，不信任模型輸出（D-94）；三道有界閘（步驟 ≤24、無環、prompt 非空）不截斷；覆蓋對映；`prd_sha256` 綁凍結摘要，不符標 `STALE`；重拆＝新版本。
- **W-P12 console-api 流程**：預演 OPERATOR 以上、確認僅 ADMIN；先建 `projects` 列（`execution_path` 取自預演回應）再呼 Bridge；失敗補償＝專案列標 `ARCHIVED`＋稽核，不自動清理；`approver` 一律取 JWT subject；`route` 與 `decomposition` 的 Bridge 讀逾時 330 秒（D-105）。
- **W-P13 SCR**：兩型（MINOR、MAJOR）加自癒耗盡路徑；console-api 先呼既有 stop 用例再呼 Bridge `:scr`（D-103）；MINOR 於 `:approve-baseline` 偵測 OPEN 的 MINOR 時以 `Gate-0-SCR<k>` 凍結並同請求套用，失敗留 `APPROVED` 並可 `:scr-apply` 重試；`scr_limit` 為同研究專案 MINOR（OPEN、APPROVED、APPLIED）已有 2 筆（D-104）；SCR 期間內環唯讀（`scr_open`）。
- **W-P14 角色**：`route/preview`、`scr`、`decomposition`、`decomposition/signoff` 為 OPERATOR 以上；`route`、`scr/*/apply` 僅 ADMIN；三個 GET 為 VIEWER 以上。
- **W-P15 reason 四處同改**：後端 `ErrorReasons`、前端 `RESEARCH_REASONS`、契約 §0.2、Architecture §11.1 的集合相等（P0 的 22 個、P0 尾巴 4 個、P1 的 9 個）；不進 `lib/api/reasons.ts`。
- **W-P16 能力探針**：十三鍵不變；UI 停用只是體驗，伺服器端仍驗證（API 直呼預演在不支援部署回 422）。
- **W-P17 前端呈現**：外部與 LLM 文字一律純文字渲染；VIEWER 寫入控件停用且 `title` 為「權限不足（唯讀角色）」；游標取自 API 不取瀏覽器儲存；SSE 事件加 REST 回補。
- **W-P18 步驟接入**：`?step=route`、`?step=build` 為真面板，`?step=deliver` 仍為占位；說明三道鎖綠且計數不變（`HELP_PAGES` 22、`HELP_ROUTES` 25、`StateTableId` 19）。
- **W-P19 對帳**：只報告不修復；六項檢查固定；`route_decision` 與 `task_decomposition` 兩項改為真比對（兩側皆缺席仍 ok 且 `present` 為假）；分流時點自動對帳入庫。
- **W-P20 完整率口徑**：R7＝路由列、R8＝拆解列、R10＝視圖、R11＝交付列、R12＝SCR 列（⚖P1-16）。
- **W-P21 hermetic**：AT 不連外部網路；真 git 只在暫存拋棄式 clone；`gh` 一律假；真 `claude` 不用；時間以假時鐘注入。
- **W-P23 TCS 凍結後游標（D-125）**：TCS 經既有 `:freeze` 凍結後 DB 游標仍為 `build／TCS_PENDING`：讀端衍生（`ResearchFlowPolicy.effective` 於 `TCS_PENDING` 且 `stage2Frozen` 回 `build／BUILD_READY／IDLE`）；Bridge `:reconcile` 於 `TCS_PENDING × Stage-2 已凍結` 同交易校正為 `build／ROUTED／IDLE` 並記 `research.step`（`reason=tcs_frozen_correction`）；console-api 既有 SDD freeze 服務成功後、專案綁研究專案時呼 Bridge `:reconcile`（console-api 零寫入）；未凍結一律不校正。
- **W-P22 文件連動**：上位文件的訂正只走勘誤表並於 RELEASE_READY 一併 refreeze；入庫文件不得有「passed 或 skipped 字樣加四位數字」同行。

### 增量追溯表（上位凍結檔；digest＝主控落檔時以 `Get-FileHash -Algorithm SHA256` 對工作樹逐檔現算，Stage-1 凍結由 CLI 重算為準；本檔不填任何 sha256；D-89：與 P0 鍵同一組十檔，取工作樹現行版本含勘誤）

| 上位檔 | 路徑（相對 monorepo 根） | sha256 |
|--------|--------------------------|--------|
| Console PRD（§0.9 研究指標、§8.1 導覽註） | `docs/01_requirements/Agent_ConsoleUI_PRD.md` | `87dd6c9ba917ed0296eb923e7e6122cb4d5f6afb9c5bc06ab39143a0a9924660` |
| Architecture（K.4 V19 DDL、§5.4、§10、§11.1） | `AgentConsole/docs/02_architecture/Architecture.md` | `4ece7ab7fe57bb8c2fce4b06b3ab982d7147f27be3fc23d7cf5b4b785a8cd17d` |
| ADR-001（技術棧鎖定） | `AgentConsole/docs/02_architecture/ADR-001-TechStack-Lock.md` | `ff0bcd0038b77e80885240d287cfc68fb55c02200dc59f62f7e59c7691094e38` |
| ADR-002（前端設計系統） | `AgentConsole/docs/02_architecture/ADR-002-Frontend-Design-System.md` | `b0897c536bdbce19efc21bf0762240f22e054fc4ff03882276fa0ed59da6066d` |
| API 契約 P3-6（附錄 B reason 表；`reasons.test.ts` 的雙向鎖對象） | `AgentConsole/docs/02_architecture/API_Contract_P3-6.md` | `0ada38cf4fe438c4fd572a89cc3af089711361339c62e01653ef2438cefe2300` |
| OpenAPI 快照 P3-6 | `AgentConsole/docs/02_architecture/openapi-p3-6.yaml` | `956539977c70fe6527c7d41162cc49a6d6138c5a49d35d7a43c4852a6bf87823` |
| ResearchToPRD PRD（含勘誤） | `docs/01_requirements/ResearchToPRD_PRD.md` | `a6d7138640a881c52d0169ee1e49c91dfabd155c76f7d3eb04a79165f8cbc31c` |
| ADR-003（載體、持久化、流程脊、D8、D14～D16） | `AgentConsole/docs/02_architecture/ADR-003-ResearchToPRD.md` | `214c7920a654d0de18d5d8154dc44b3e7f009c2c78f95329c62b246adc424e5e` |
| ADR-XPLAT-017（Bridge 研究寫入面；D2、D5、附錄 A） | `docs/04_planning/ADR/ADR-XPLAT-017-bridge-fsm-write-surface.md` | `cf24c5cdd170e230956b7faf9806ed1027678df28858ac1635fc7e689c013bb4` |
| API 契約 ResearchToPRD v1.0（含勘誤） | `AgentConsole/docs/02_architecture/API_Contract_ResearchToPRD.md` | `b498fc1e3a6164669b3cc96dd434b73ebf1e7faaa2b12c048154933ab048a211` |

---
## 1. AC → AT 映射表

> **AT ID 文法**：`AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`，前兩段數字＝所屬 AC；邊界、錯誤與負控 AT 以 `AT-961-<n>-E-<m>` 命名並列於本節。測試類型為 Unit／Integration／Contract／E2E／Gate。各 AT 的判定指令與測試檔見 §3 各 AT 末行。本鍵 Java 與 TS 的 AT 走徑②（SDD session-only）、**不入 evaluator**；Bridge 的 AT 可走徑①或徑②（見 §2）。
### 1.1 AC-961-n 的 Given／When／Then（契約級）
- **AC-961-1** 資料庫 V19：分流、SCR、拆解、交付表與自癒視圖的不可變與 CHECK（Flyway V19）
  - 主責包與規則：PKG-DB-P1；W-P1、W-P10
  - 對應 PRD：AC-R2P-02-7、AC-R2P-02-8
  - Given 套用 V1～V19 的 PostgreSQL 18 When 對 V19 的五張表與視圖做 INSERT、UPDATE、DELETE 與越界值寫入 Then CHECK、部分唯一索引、受控更新守衛（四張）與 append-only 守衛（交付表）依 Architecture K.4 逐條拒絕，時間欄皆為帶時區型別，視圖不可寫。
- **AC-961-2** 分流輸入閘與消毒（Bridge route 驗證層）
  - 主責包與規則：PKG-BR-D；W-P2、W-P3
  - 對應 PRD：AC-R2P-11-1、AC-R2P-11-4、AC-R2P-11-5、AC-R2P-12-3、AC-R2P-13-3、AC-R2P-13-7
  - Given 分流請求本文 When 預演或確認 Then 欄位值域、字元集、路徑、分支名、庫名、可見性、範本與落點目標先過同一套驗證，違規以 422 逐欄列出且零副作用。
- **AC-961-3** 分流預演：動作清單與零副作用、部署不支援
  - 主責包與規則：PKG-BR-D；W-P2、W-P3
  - 對應 PRD：AC-R2P-11-2、AC-R2P-11-6、AC-R2P-12-1、AC-R2P-13-1、AC-R2P-13-6
  - Given 合法的卡 A 或卡 B 參數 When POST route-preview Then 回與執行共用的動作清單（動作、目標、是否觸及外部系統），前後 git 狀態、目標目錄與資料庫皆相同；部署不支援時回結構化缺項。
- **AC-961-4** 分流執行：逐步入庫、失敗停點、重試、衝突與事件
  - 主責包與規則：PKG-BR-D；W-P1、W-P2、W-P4
  - 對應 PRD：AC-R2P-11-3、AC-R2P-11-8、AC-R2P-12-5、AC-R2P-13-4
  - Given 預演通過且 ADMIN 確認 When 執行 Then 步驟依序執行並逐步入庫，全部成功才寫 route_decision.json 並推進游標到 build；部分失敗停在第 3 步、已成功步驟不重做、可重試；同專案不得有第二個進行中的分流。
- **AC-961-5** 軌道 A：獨立 worktree、發佈、落點 stub 與主工作樹零擾動
  - 主責包與規則：PKG-BR-D；W-P2、W-P5
  - 對應 PRD：AC-R2P-12-1、AC-R2P-12-2、AC-R2P-12-4、AC-R2P-12-5、AC-R2P-12-6
  - Given 卡 A 確認 When 執行 Then 於獨立 worktree 建立 feature 分支、發佈位元組相同的 PRD 複本與落點 stub、綁定 Console 專案，主工作樹 HEAD 與狀態前後相同，治理檔零變更。
- **AC-961-6** 軌道 B：範本展開、工作區複製、git 與 gh、token 零外洩
  - 主責包與規則：PKG-BR-D；W-P2、W-P6、W-P7
  - 對應 PRD：AC-R2P-13-2、AC-R2P-13-4、AC-R2P-13-5、AC-R2P-13-8
  - Given 卡 B 確認 When 執行 Then 於 BRIDGE_SCAFFOLD_ROOT 下以確定性模板建立新專案、複製研究工作區並逐檔驗證、初始 commit 不含 raw 與 .env、gh 只經白名單，token 不出現在任何落地面。
- **AC-961-7** 內環鍵建立與 Stage-1 基線採納（FSM 序列）
  - 主責包與規則：PKG-BR-D；W-P8
  - 對應 PRD：AC-R2P-11-3、AC-R2P-11-7、AC-R2P-14-7
  - Given 分流確認 When 執行內環收尾 Then Bridge 於目標根以 show 建內環鍵、五次 transition、spec-frozen --stage Stage-1，其 show 輸出的 PRD 摘要等於外環 Gate 0 凍結摘要，外環鍵不被改動。
- **AC-961-8** gitops 白名單、能力登記與 FSM 單一寫入面（AST 與表驅動鎖）
  - 主責包與規則：PKG-BR-D；W-P3、W-P9
  - 對應 PRD：AC-R2P-11-5、AC-R2P-11-7、AC-R2P-13-4
  - Given Bridge 原始碼與 gitops 模組 When 以表驅動與 AST 掃描 Then git 與 gh 子行程只住 gitops、只准白名單形態、使用者片段先過列舉或正規式、新模組先登記，FSM 寫入仍只經 fsm_ops 與 sdd_cli。
- **AC-961-9** TCS 草擬 stage（tcs-draft）
  - 主責包與規則：PKG-BR-D；W-P8、W-P10
  - 對應 PRD：AC-R2P-14-7
  - Given 內環鍵已 Stage-1 採納 When OPERATOR 啟動 tcs-draft Then 以最小授權的 spec-engineer run 草擬 TCS、預檢、發佈到目標 docs 並登記雜湊，凍結走既有 :freeze，凍結前內環 run 啟動回 409。
- **AC-961-10** 任務拆解：草稿、有界閘、覆蓋對映與 stale
  - 主責包與規則：PKG-BR-D；W-P11
  - 對應 PRD：AC-R2P-14-1、AC-R2P-14-2、AC-R2P-14-5、AC-R2P-14-6
  - Given 分流完成且 PRD 已凍結 When 觸發拆解 Then 產生 signed_off 為假的草稿與 R8 列，三道有界閘不截斷，每個 AC 被覆蓋或列為未覆蓋，PRD 摘要變更後標 STALE。
- **AC-961-11** 拆解簽核與執行閘（console-api 二次校驗）
  - 主責包與規則：PKG-API-P1；W-P11、W-P12
  - 對應 PRD：AC-R2P-14-1、AC-R2P-14-2、AC-R2P-14-3、AC-R2P-14-4、AC-R2P-14-5、AC-R2P-14-7
  - Given 拆解草稿 When OPERATOR 簽核或有人嘗試啟動執行 Then 簽核經既有 signoff 路徑落正式專案，未簽核、stale、TCS 未凍結與 SCR 開啟時啟動一律 409。
- **AC-961-12** SCR 後端：發起、輸入閘、上限、MAJOR 與自癒耗盡路徑
  - 主責包與規則：PKG-BR-D；W-P13
  - 對應 PRD：AC-R2P-19-1、AC-R2P-19-3、AC-R2P-19-4、AC-R2P-19-5、AC-R2P-19-6、AC-R2P-19-7
  - Given 內環進行中 When OPERATOR 發起 SCR Then 依型別與來源類別寫 research_scr 列、停止進行中 run、新的執行回 409，輸入違規逐筆列出，同 Stage 的 MINOR 至多 2 次，自癒耗盡只產生指令。
- **AC-961-13** SCR MINOR 的 FSM 指令序列與內環現態矩陣
  - 主責包與規則：PKG-BR-D；W-P13
  - 對應 PRD：AC-R2P-19-2、AC-R2P-19-4、AC-R2P-19-8
  - Given MINOR SCR 與內環現態 When 執行收尾序列 Then 依序 transition SPEC_AUDIT、發佈新 PRD、spec-refreeze、transition PR_REVIEW、gate PR_REVIEW FAIL，序列與人工等價序列的 decision_trace 相同，現態不在矩陣內回 409。
- **AC-961-14** console-api 分流端點：預演、確認、先建專案列與補償
  - 主責包與規則：PKG-API-P1；W-P12、W-P14
  - 對應 PRD：AC-R2P-11-2、AC-R2P-11-3、AC-R2P-11-4、AC-R2P-11-6、AC-R2P-11-8、AC-R2P-12-4、AC-R2P-13-4
  - Given 分流請求 When 經 console-api Then 輸入閘先於 Bridge、確認僅 ADMIN、先建 projects 列再呼 Bridge、失敗補償到安全態且不自動清理，token 不外洩，稽核各留一列。
- **AC-961-15** console-api SCR、拆解端點、角色矩陣、OpenAPI 與 reason 契約
  - 主責包與規則：PKG-API-P1；W-P12、W-P15
  - 對應 PRD：AC-R2P-11-1、AC-R2P-11-4、AC-R2P-14-1、AC-R2P-14-5、AC-R2P-19-1、AC-R2P-19-5、AC-R2P-19-6、AC-R2P-21-2
  - Given P1 端點 When 三種角色與匿名呼叫 Then 角色矩陣、OpenAPI 路徑與操作計數、reason 四處集合、ArchUnit 零寫入與源頭鎖皆與契約一致。
- **AC-961-16** capabilities 能力探針與 UI 停用
  - 主責包與規則：PKG-BR-D；W-P6、W-P16
  - 對應 PRD：AC-R2P-04-11、AC-R2P-11-6、AC-R2P-13-7
  - Given 本機模式與容器模式 When 讀 capabilities 與 health/deep Then 五個分流相關鍵取真值、鍵集合不變，容器模式預演回缺項，UI 依缺項停用並說明。
- **AC-961-17** 前端 RouteDrawer 與步驟 3 面板
  - 主責包與規則：PKG-FE-D；W-P17
  - 對應 PRD：AC-R2P-11-1、AC-R2P-11-2、AC-R2P-11-3、AC-R2P-11-4、AC-R2P-11-5、AC-R2P-11-6、AC-R2P-12-3、AC-R2P-13-3、AC-R2P-13-7
  - Given 研究專案在第 3 步 When 開啟面板 Then 卡 A 與卡 B、評估維度表、預演面板、角色停用、差異理由、Public 確認、逐步進度、失敗重試與完成摘要皆符合契約。
- **AC-961-18** 前端步驟 4 前半面板：拆解、覆蓋、簽核與 TCS 草擬
  - 主責包與規則：PKG-FE-D；W-P17
  - 對應 PRD：AC-R2P-14-1、AC-R2P-14-2、AC-R2P-14-3、AC-R2P-14-5、AC-R2P-14-7
  - Given 研究專案在第 4 步 When 開啟面板 Then 拆解草稿樹、覆蓋矩陣、豁免與簽核、stale、TCS 草擬狀態與到既有 freeze、import、execute 的連結皆符合契約，看板與自癒屬 P2。
- **AC-961-19** 步驟接入、說明三道鎖、端點函式與前端靜態鎖
  - 主責包與規則：PKG-FE-D；W-P17、W-P18
  - 對應 PRD：AC-R2P-21-2、AC-R2P-21-5
  - Given P1 交付 When 開啟 route 與 build 步驟 Then 不再是占位、deliver 仍為占位，說明與狀態表接入且三道鎖綠，端點函式數與型別與契約逐一對應，靜態鎖遵守。
- **AC-961-20** 對帳：route_decision、task_decomposition 與 SCR 相態
  - 主責包與規則：PKG-BR-D；W-P19
  - 對應 PRD：AC-R2P-23-1、AC-R2P-23-4
  - Given 一個已分流並拆解的研究專案 When 呼叫對帳或到達分流時點 Then 兩個新檢查項依 DB 與檔案判定、FSM 與游標對映表含 P1 相態、分流時點自動對帳入庫且不修任何一邊。
- **AC-961-21** 入庫完整率與稽核列（V19 口徑）
  - 主責包與規則：PKG-API-P1；W-P12、W-P20
  - 對應 PRD：AC-R2P-02-4、AC-R2P-02-5
  - Given 已分流並簽核拆解的專案 When 查 records/audit 與 audit_log Then R7、R8 有筆數、missing 恰為尚未交付者，ADMIN 確認分流與簽核拆解各有一列 2xx 稽核且與 R7、R8 同 trace_id。
- **AC-961-22** 整合 P1：拋棄式 clone、假 gh、Docker mock 與 Playwright 真棧
  - 主責包與規則：整合 P1；W-P21
  - 對應 PRD：AC-R2P-11-2、AC-R2P-11-6、AC-R2P-11-7、AC-R2P-12-1、AC-R2P-13-4、AC-R2P-14-7、AC-R2P-19-8、AC-R2P-21-5
  - Given 拋棄式 clone、暫存 scaffold 根與假 gh When 走完軌道 A、軌道 B、拆解、TCS 草擬與 SCR MINOR Then PRD 8.1 P1 出口 (a) 至 (k) 皆有證據，Docker mock-only 下 UI 停用且 API 直呼回缺項。
- **AC-961-23** 邊界、跨平台與衛生閘（允許變更集合、禁區、無新守衛、無新目錄項原語）
  - 主責包與規則：PKG-DOC1；W-P10、W-P22
  - 對應 PRD：AC-R2P-02-7
  - Given 本鍵全部變更 When 以 git diff 與靜態工具核對 Then 只動各包允許集合、禁區零差異、不新增 hook 與守衛與目錄項原語站點、Python 衛生規則與跨平台閘綠。
- **AC-961-24** 文件連動、追溯與 V 系列
  - 主責包與規則：PKG-DOC1；W-P22
  - 對應 PRD：AC-R2P-21-6
  - Given 本鍵文件與 RTM 子表 When 跑文件閘與核對 Then 無測試摘要同行四位數、RTM 每列回填、編號不撞號、Architecture 5.4 檢查表逐項有交付、V 系列以文字證據落檔。
- **AC-961-25** TCS 凍結後的游標校正（D-125）：讀端衍生、Bridge 對帳校正、凍結後觸發與重新對帳
  - 主責包與規則：PKG-API-P1／PKG-BR-D2／PKG-FE-D2；W-P23
  - 對應 PRD：AC-R2P-14-7、AC-R2P-23-1
  - Given TCS 經既有 :freeze 於內環鍵凍結 Stage-2 而 DB 游標仍為 build／TCS_PENDING When 讀專案、對帳或凍結服務成功 Then 讀端衍生為 build／BUILD_READY／IDLE，Bridge 對帳同交易校正為 build／ROUTED／IDLE 並記事件，既有凍結服務成功後對綁研究專案的專案呼叫對帳，未凍結時一律不校正。

### 1.2 PRD 屬 P1 的 AC-R2P → AC-961-n → AT 全表（47 條，逐條不漏）
> P1 判定依 PRD §3.1 與 §8.1：FR-R2P-11～14（共 29 條）、FR-R2P-19（8 條；後端與 FSM 序列證據，UI 子句標「P2 承接」）＝37 條，加增量半條 10 條（FR-R2P-02 的 V19 與稽核與完整率、FR-R2P-04-11、FR-R2P-21 的說明與步驟接入、FR-R2P-23 的兩個新對帳項與分流時點；承接 TCS-P0 §1.2 備註與 §7 ⚖2、⚖3 的 P1 半）。AC-R2P-01-5 的連結與 `ResearchBackLink` 仍屬 P2（TCS-P0 ⚖2），不在本表。
| AC-R2P（P1） | AC-961 | 覆蓋的 AT | 備註 |
|---|---|---|---|
| AC-R2P-11-1 | AC-961-2、AC-961-15、AC-961-17 | AT-961-2-7、AT-961-15-9、AT-961-17-1、AT-961-17-2 |  |
| AC-R2P-11-2 | AC-961-3、AC-961-14、AC-961-17、AC-961-22 | AT-961-3-1、AT-961-3-3、AT-961-3-4、AT-961-3-E-1、AT-961-14-1、AT-961-17-5、AT-961-22-1、AT-961-22-2 |  |
| AC-R2P-11-3 | AC-961-4、AC-961-7、AC-961-14、AC-961-17 | AT-961-4-1、AT-961-4-2、AT-961-4-3、AT-961-4-4、AT-961-4-5、AT-961-4-6、AT-961-4-7、AT-961-4-8、AT-961-4-E-1、AT-961-4-E-2、AT-961-4-E-3、AT-961-7-4、AT-961-14-7、AT-961-14-8、AT-961-14-E-2、AT-961-17-7 |  |
| AC-R2P-11-4 | AC-961-2、AC-961-14、AC-961-15、AC-961-17 | AT-961-2-4、AT-961-2-E-1、AT-961-14-E-1、AT-961-15-9、AT-961-17-3、AT-961-17-6、AT-961-17-E-2 |  |
| AC-R2P-11-5 | AC-961-2、AC-961-8、AC-961-17 | AT-961-2-1、AT-961-2-2、AT-961-8-3、AT-961-17-6、AT-961-17-E-2 |  |
| AC-R2P-11-6 | AC-961-3、AC-961-14、AC-961-16、AC-961-17、AC-961-22 | AT-961-3-5、AT-961-14-1、AT-961-16-3、AT-961-16-5、AT-961-17-6、AT-961-17-8、AT-961-22-5 |  |
| AC-R2P-11-7 | AC-961-7、AC-961-8、AC-961-22 | AT-961-7-1、AT-961-7-2、AT-961-7-3、AT-961-7-4、AT-961-7-5、AT-961-7-6、AT-961-7-E-1、AT-961-7-E-2、AT-961-8-6、AT-961-22-1、AT-961-22-3 |  |
| AC-R2P-11-8 | AC-961-4、AC-961-14 | AT-961-4-9、AT-961-14-2、AT-961-14-3、AT-961-14-4、AT-961-14-5 |  |
| AC-R2P-12-1 | AC-961-3、AC-961-5、AC-961-22 | AT-961-3-1、AT-961-3-3、AT-961-3-7、AT-961-5-1、AT-961-5-2、AT-961-5-6、AT-961-22-1、AT-961-22-E-2 |  |
| AC-R2P-12-2 | AC-961-5 | AT-961-5-3 |  |
| AC-R2P-12-3 | AC-961-2、AC-961-17 | AT-961-2-3、AT-961-17-3 | 「ADMIN 維護」依 D-100 勘誤為 P1 固定四值常數（⚖P1-5） |
| AC-R2P-12-4 | AC-961-5、AC-961-14 | AT-961-5-5、AT-961-14-3、AT-961-14-7 |  |
| AC-R2P-12-5 | AC-961-4、AC-961-5 | AT-961-4-2、AT-961-4-3、AT-961-5-2、AT-961-5-E-1 |  |
| AC-R2P-12-6 | AC-961-5 | AT-961-5-4 |  |
| AC-R2P-13-1 | AC-961-3 | AT-961-3-2、AT-961-3-4、AT-961-3-5 |  |
| AC-R2P-13-2 | AC-961-6 | AT-961-6-4、AT-961-6-5、AT-961-6-6、AT-961-6-E-1 | 副本含 raw、以範本 `.gitignore` 排除入版控（D-117，⚖P1-33） |
| AC-R2P-13-3 | AC-961-2、AC-961-17 | AT-961-2-1、AT-961-2-6、AT-961-2-E-1、AT-961-17-4、AT-961-17-E-1、AT-961-17-E-2 |  |
| AC-R2P-13-4 | AC-961-4、AC-961-6、AC-961-8、AC-961-14、AC-961-22 | AT-961-4-3、AT-961-6-6、AT-961-6-7、AT-961-6-8、AT-961-6-E-2、AT-961-8-1、AT-961-8-2、AT-961-8-3、AT-961-8-4、AT-961-8-5、AT-961-8-6、AT-961-8-7、AT-961-8-E-1、AT-961-8-E-2、AT-961-14-6、AT-961-22-2、AT-961-22-E-1 |  |
| AC-R2P-13-5 | AC-961-6 | AT-961-6-5 | 同 13-2（D-117） |
| AC-R2P-13-6 | AC-961-3 | AT-961-3-6 |  |
| AC-R2P-13-7 | AC-961-2、AC-961-16、AC-961-17 | AT-961-2-5、AT-961-16-1、AT-961-16-4、AT-961-16-5、AT-961-16-E-1、AT-961-17-4 | P1 只有 `python-fastapi`；node 與 java 不在清單 |
| AC-R2P-13-8 | AC-961-6 | AT-961-6-1、AT-961-6-2、AT-961-6-3、AT-961-6-9 |  |
| AC-R2P-14-1 | AC-961-10、AC-961-11、AC-961-15、AC-961-18 | AT-961-10-1、AT-961-10-2、AT-961-10-7、AT-961-10-8、AT-961-10-E-1、AT-961-11-7、AT-961-15-2、AT-961-15-3、AT-961-15-5、AT-961-15-6、AT-961-15-7、AT-961-15-8、AT-961-18-1、AT-961-18-6、AT-961-18-7 |  |
| AC-R2P-14-2 | AC-961-10、AC-961-11、AC-961-18 | AT-961-10-3、AT-961-10-4、AT-961-11-1、AT-961-18-1、AT-961-18-2、AT-961-18-E-1 |  |
| AC-R2P-14-3 | AC-961-11、AC-961-18 | AT-961-11-1、AT-961-11-2、AT-961-11-E-1、AT-961-18-2、AT-961-18-5 |  |
| AC-R2P-14-4 | AC-961-11 | AT-961-11-3、AT-961-11-5、AT-961-11-E-2 |  |
| AC-R2P-14-5 | AC-961-10、AC-961-11、AC-961-15、AC-961-18 | AT-961-10-5、AT-961-11-4、AT-961-15-2、AT-961-15-4、AT-961-15-5、AT-961-18-3、AT-961-18-5 |  |
| AC-R2P-14-6 | AC-961-10 | AT-961-10-6 |  |
| AC-R2P-14-7 | AC-961-7、AC-961-9、AC-961-11、AC-961-18、AC-961-22、AC-961-25 | AT-961-7-7、AT-961-9-1、AT-961-9-2、AT-961-9-3、AT-961-9-4、AT-961-9-5、AT-961-9-6、AT-961-9-7、AT-961-9-E-1、AT-961-9-E-2、AT-961-11-6、AT-961-18-4、AT-961-22-3、AT-961-25-1、AT-961-25-2、AT-961-25-3、AT-961-25-4、AT-961-25-E-1 | TCS 凍結前內環 run 啟動 409 由 console-api 單一前置守衛承擔（D-102，⚖P1-29） |
| AC-R2P-19-1 | AC-961-12、AC-961-15 | AT-961-12-1、AT-961-12-7、AT-961-12-E-1、AT-961-12-E-2、AT-961-15-1、AT-961-15-3、AT-961-15-4、AT-961-15-6、AT-961-15-8、AT-961-15-E-1 | 後端與 FSM 序列證據屬 P1；看板上的發起鈕與橫幅屬 P2 承接；「內環鍵回 IMPLEMENTATION」依 D-115(b)-7 勘誤為現態不變 |
| AC-R2P-19-2 | AC-961-13 | AT-961-13-1、AT-961-13-6、AT-961-13-E-1 |  |
| AC-R2P-19-3 | AC-961-12 | AT-961-12-3、AT-961-12-7 |  |
| AC-R2P-19-4 | AC-961-12、AC-961-13 | AT-961-12-5、AT-961-13-7 | P1 驗游標、`SCR_OPEN` 與 stepper 文字標示「SCR 進行中」；橫幅屬 P2 承接 |
| AC-R2P-19-5 | AC-961-12、AC-961-15 | AT-961-12-2、AT-961-15-1 | console-api 與 Bridge 的輸入閘屬 P1；UI 發起表單屬 P2 承接 |
| AC-R2P-19-6 | AC-961-12、AC-961-15 | AT-961-12-4、AT-961-15-4 |  |
| AC-R2P-19-7 | AC-961-12 | AT-961-12-6 |  |
| AC-R2P-19-8 | AC-961-13、AC-961-22 | AT-961-13-1、AT-961-13-2、AT-961-13-3、AT-961-13-4、AT-961-13-5、AT-961-13-8、AT-961-13-9、AT-961-13-E-2、AT-961-13-E-3、AT-961-22-4 | SCR 序列的 `gate` 呼叫與 D-45 的並存見 ⚖P1-27 |
| AC-R2P-02-4 | AC-961-21 | AT-961-21-1 | 部分（承接 TCS-P0 ⚖3）：P1 驗 V19 口徑下 R7、R8 有筆數、完成分流與簽核的專案 `missing` 恰 R11；已交付專案 `missing` 為空屬 P2（AC-R2P-20-6）（⚖P1-16） |
| AC-R2P-02-5 | AC-961-21 | AT-961-21-2、AT-961-21-E-1 | 部分（承接 TCS-P0 ⚖3）：P1 驗分流確認與簽核拆解兩類稽核列；Release Tag 屬 P2 |
| AC-R2P-02-7 | AC-961-1、AC-961-23 | AT-961-1-1、AT-961-1-2、AT-961-1-3、AT-961-1-4、AT-961-1-5、AT-961-1-6、AT-961-1-7、AT-961-1-8、AT-961-1-9、AT-961-1-E-1、AT-961-1-E-2、AT-961-1-E-3、AT-961-23-1、AT-961-23-2、AT-961-23-3、AT-961-23-4、AT-961-23-5、AT-961-23-E-1 | P1 半條：V19 五張表的 CHECK、觸發器、部分唯一索引與 append-only |
| AC-R2P-02-8 | AC-961-1 | AT-961-1-1 | P1 半條：V19 五表時間欄皆帶時區 |
| AC-R2P-04-11 | AC-961-16 | AT-961-16-1、AT-961-16-2、AT-961-16-3、AT-961-16-4、AT-961-16-5、AT-961-16-E-2 | P1 半條：本機模式與容器模式的 capabilities 值與 UI 停用（十三鍵不變，⚖P1-2） |
| AC-R2P-21-2 | AC-961-15、AC-961-19 | AT-961-15-E-2、AT-961-19-2、AT-961-19-3、AT-961-19-E-1 | P1：route 與 build 兩步說明寫實，三道鎖與計數不變 |
| AC-R2P-21-5 | AC-961-19、AC-961-22 | AT-961-19-1、AT-961-19-4、AT-961-19-5、AT-961-19-6、AT-961-22-5、AT-961-22-6、AT-961-22-7、AT-961-22-8 | P1 版：route 與 build 為真面板，deliver 仍占位（P2 取代） |
| AC-R2P-21-6 | AC-961-24 | AT-961-24-1 | P1 的 SCG-4 檢查表由 V-C1 與 AT-961-24-1 承擔 |
| AC-R2P-23-1 | AC-961-20、AC-961-25 | AT-961-20-1、AT-961-20-2、AT-961-20-3、AT-961-20-E-1、AT-961-20-E-2、AT-961-20-E-3、AT-961-20-E-4、AT-961-25-2、AT-961-25-E-1 | P1 半條：`route_decision` 與 `task_decomposition` 兩項取真比對 |
| AC-R2P-23-4 | AC-961-20 | AT-961-20-4 | P1 半條：分流時點；交付時點屬 P2 |

### 1.3 本檔範圍外：PRD 屬 P2 的 AC-R2P（23 條）
> 這些 AC 不由本 TCS 驗收，不得在本鍵 RELEASE 時被算作已覆蓋；它們由鍵 `agentconsole-research-to-prd-p2` 的 TCS 承接（D-93：TCS-P2 於 P1 第二波派出後由 SD 開工）。另：AC-R2P-01-5 的開啟執行中心與監控中心連結與 `ResearchBackLink` 屬 P2（TCS-P0 ⚖2）；FR-R2P-19 的看板發起鈕與橫幅（UI 子句）屬 P2；AC-R2P-02-4 的已交付專案 `missing` 為空與 AC-R2P-02-5 的 Release Tag 稽核屬 P2。
| AC-R2P（本檔範圍外） | 期別 | 所屬 FR | 承接 |
|---|---|---|---|
| AC-R2P-15-1 | P2 | FR-R2P-15 執行看板五階段 | 鍵 agentconsole-research-to-prd-p2 的 TCS |
| AC-R2P-15-2 | P2 | FR-R2P-15 執行看板五階段 | 鍵 agentconsole-research-to-prd-p2 的 TCS |
| AC-R2P-15-3 | P2 | FR-R2P-15 執行看板五階段 | 鍵 agentconsole-research-to-prd-p2 的 TCS |
| AC-R2P-15-4 | P2 | FR-R2P-15 執行看板五階段 | 鍵 agentconsole-research-to-prd-p2 的 TCS |
| AC-R2P-15-5 | P2 | FR-R2P-15 執行看板五階段 | 鍵 agentconsole-research-to-prd-p2 的 TCS |
| AC-R2P-15-6 | P2 | FR-R2P-15 執行看板五階段 | 鍵 agentconsole-research-to-prd-p2 的 TCS |
| AC-R2P-16-1 | P2 | FR-R2P-16 自癒監視器 | 鍵 agentconsole-research-to-prd-p2 的 TCS |
| AC-R2P-16-2 | P2 | FR-R2P-16 自癒監視器 | 鍵 agentconsole-research-to-prd-p2 的 TCS |
| AC-R2P-16-3 | P2 | FR-R2P-16 自癒監視器 | 鍵 agentconsole-research-to-prd-p2 的 TCS |
| AC-R2P-16-4 | P2 | FR-R2P-16 自癒監視器 | 鍵 agentconsole-research-to-prd-p2 的 TCS |
| AC-R2P-16-5 | P2 | FR-R2P-16 自癒監視器 | 鍵 agentconsole-research-to-prd-p2 的 TCS |
| AC-R2P-17-1 | P2 | FR-R2P-17 即時終端窗格 | 鍵 agentconsole-research-to-prd-p2 的 TCS |
| AC-R2P-17-2 | P2 | FR-R2P-17 即時終端窗格 | 鍵 agentconsole-research-to-prd-p2 的 TCS |
| AC-R2P-17-3 | P2 | FR-R2P-17 即時終端窗格 | 鍵 agentconsole-research-to-prd-p2 的 TCS |
| AC-R2P-17-4 | P2 | FR-R2P-17 即時終端窗格 | 鍵 agentconsole-research-to-prd-p2 的 TCS |
| AC-R2P-18-2 | P2 | FR-R2P-18 人機協同決策彈窗（類型 b、c、d；類型 a 屬 P0） | 鍵 agentconsole-research-to-prd-p2 的 TCS |
| AC-R2P-18-3 | P2 | FR-R2P-18 人機協同決策彈窗（類型 b、c、d；類型 a 屬 P0） | 鍵 agentconsole-research-to-prd-p2 的 TCS |
| AC-R2P-20-1 | P2 | FR-R2P-20 交付驗收與歸檔 | 鍵 agentconsole-research-to-prd-p2 的 TCS |
| AC-R2P-20-2 | P2 | FR-R2P-20 交付驗收與歸檔 | 鍵 agentconsole-research-to-prd-p2 的 TCS |
| AC-R2P-20-3 | P2 | FR-R2P-20 交付驗收與歸檔 | 鍵 agentconsole-research-to-prd-p2 的 TCS |
| AC-R2P-20-4 | P2 | FR-R2P-20 交付驗收與歸檔 | 鍵 agentconsole-research-to-prd-p2 的 TCS |
| AC-R2P-20-5 | P2 | FR-R2P-20 交付驗收與歸檔 | 鍵 agentconsole-research-to-prd-p2 的 TCS |
| AC-R2P-20-6 | P2 | FR-R2P-20 交付驗收與歸檔 | 鍵 agentconsole-research-to-prd-p2 的 TCS |

### 1.4 機械鎖與出口判準的對照

**PRD §9.4 機械鎖與 ADR-XPLAT-017 §5 測試鎖（P1 部分）→ AT**（每項至少一個 AT；本表由自查腳本逐一核對 AT 存在）

| 鎖 | 來源 | 對應 AT |
|----|------|---------|
| ① ArchUnit 字串掃描：console-api 對 `research_*`（含 V19 五表）零寫入 | PRD §9.4 ① | AT-961-15-5 |
| ② Bridge AST：FSM 單一寫入面、`create_key` 呼叫者集合、`apply_minor` 不呼叫 `approve_baseline`、SCR 的自癒耗盡分支零 FSM 寫入、子行程只經 `procutil` | PRD §9.4 ②；ADR-XPLAT-017 §5 | AT-961-8-4、AT-961-8-6、AT-961-8-7 |
| ④ 能力登記：git 與 gh 子行程只住 `gitops.py`；新模組先登記 | PRD §9.4 ④ | AT-961-8-5 |
| ⑤ token 脫敏夾具（含假 token） | PRD §9.4 ⑤ | AT-961-6-7、AT-961-6-E-2、AT-961-14-6 |
| ⑦ `ResearchSchemaMigrationIT` 的 CHECK、觸發器與部分唯一索引斷言（V19） | PRD §9.4 ⑦ | AT-961-1-2、1-3、1-4、1-5、1-6、1-7、1-8、1-9、1-E-1、1-E-3 |
| 動詞表不變（`RESEARCH_VERBS` 五個；`resume-from-escalation` 不入） | ADR-XPLAT-017 §5 | AT-961-8-7、AT-961-7-5、AT-961-12-6 |
| 暫存狀態目錄實跑：採納序列、Stage-2、SCR MINOR 序列的 `decision_trace` | ADR-XPLAT-017 附錄 A | AT-961-7-1、AT-961-9-4、AT-961-13-1、AT-961-22-4 |
| 既有 `:freeze` 對無 TCS 仍 422 | ADR-XPLAT-017 D3 | AT-961-9-5 |
| `tcs gate` 第二理由前綴（D-97）的正負控 | D-97 | AT-961-7-7 |
| 預演零副作用（D-108） | PRD AC-R2P-11-2 | AT-961-3-3、AT-961-3-4、AT-961-14-1、AT-961-22-1 |
| 執行前置守衛三個 409 與非研究專案零影響（D-102） | D-102 | AT-961-11-3、11-4、11-5、11-6、11-E-2 |
| TCS 凍結後游標：讀端衍生、`:reconcile` 校正、凍結後觸發、未凍結不校正（D-125） | D-125 | AT-961-25-1、25-2、25-3、25-4、25-E-1 |
| 範本內 Python 檔不被 `app/` 全樹 AST 鎖與 CAPABILITY 登記掃到（`.tmpl`） | ⚖P1-18 | AT-961-2-5、AT-961-6-1、AT-961-8-5 |

**PRD §8.1 P1 出口 (a)～(k) → AT 與 V**

| 出口 | 對應 |
|------|------|
| (a) 軌道 A 於拋棄式 clone、軌道 B 於暫存 scaffold 根加假 gh 各一次端到端；另掌舵者以 Private 測試庫真機一次軌道 B | AT-961-22-1、AT-961-22-2、AT-961-22-E-2、V-H3（D-92）、V-D2 |
| (b) 預演零副作用負控 | AT-961-3-3、AT-961-3-4、AT-961-22-1 |
| (c) 軌道 A 主工作樹零擾動 | AT-961-5-1、AT-961-5-6、AT-961-22-1 |
| (d) 內環鍵 Stage-1 採納與 Stage-2 TCS 的 `show` 逐字證據 | AT-961-7-1、AT-961-7-2、AT-961-9-4、AT-961-22-1、AT-961-22-3、AT-961-25-2 |
| (e) 拆解經簽核且每個 AC 已覆蓋或有人工豁免 | AT-961-10-3、AT-961-10-4、AT-961-11-1、V-D2 |
| (f) token 零外洩負控 | AT-961-6-7、AT-961-6-8、AT-961-14-6、AT-961-22-2 |
| (g) SCR MINOR 序列證據 | AT-961-13-1、AT-961-13-2、AT-961-22-4 |
| (h) 分流時點對帳 ok | AT-961-20-4、AT-961-22-1、AT-961-22-2 |
| (i) 未簽核草稿啟動執行回 409 | AT-961-11-3、V-D2 |
| (j) V-R8 結果入證據檔 | §6.2 V-R8 |
| (k) capabilities 缺 gh 與 scaffold 時 UI 停用的 AT | AT-961-16-3、AT-961-16-5、AT-961-22-5 |

**P0 未結項分流（RISKS (c)；D-115）**

| 項 | 分流 | 本檔承接 |
|----|------|----------|
| R-1 allowlist 404 訊息 | 歸 P1（API-P1，D-123） | AT-961-15-E-2（API-P1，D-123） |
| R-2 Bridge 另四個 reason 未入四方鎖 | 歸 API-P1 | AT-961-15-4（⚖P1-25） |
| R-3 20-4 掃描自我命中 | 歸 P2 | 不在本檔 |
| R-4 FIX 包允許集合 | 歸本檔寫法 | 〈提交順序與責任〉的 FIX 包條款與 §5.7 |
| N-01、N-02、引擎步驟逾時可設定、根層幽靈符號索引、研究範圍修訂端點 | 延後（再開症狀見 RISKS (c)） | 不在本檔 |
| 前端三個衍生相態標籤 | 歸 FE-D1 | AT-961-19-E-1、AT-961-19-3 |
| BLOCKED_DB 游標校正時機 | 歸 BR-D2 | AT-961-4-E-1（⚖P1-21） |
| 真棧 spec helper 合併 | 歸 FE-W | AT-961-22-8 |
| V19 視圖與 `snapshotOfExistingTables` | 歸 DB-P1 | AT-961-1-E-2 |


### 1.5 AC → AT 映射（機器可讀；每列一個 AT）

| AC | AC 描述 | AT | AT 描述 | 自動化 | 測試類型 | 狀態 |
|----|---------|----|---------|-------|---------|------|
| AC-961-1 | 資料庫 V19：分流、SCR、拆解、交付表與自癒視圖的不可變與 CHECK（Flyway V19） | AT-961-1-1 | Flyway 歷史 1～19 全成功；V19 的五張表與一個視圖齊備且只在 console schema；ddl-auto validate 不報錯。 | ✅ | Integration | □ |
| AC-961-1 | 資料庫 V19：分流、SCR、拆解、交付表與自癒視圖的不可變與 CHECK（Flyway V19） | AT-961-1-2 | research_route_decisions 的 CHECK：軌道與目標種類與模組三者一致、列舉值、PUBLIC 只准軌道 B、狀態列舉。 | ✅ | Integration | □ |
| AC-961-1 | 資料庫 V19：分流、SCR、拆解、交付表與自癒視圖的不可變與 CHECK（Flyway V19） | AT-961-1-3 | ux_research_route_active 部分唯一索引：同一研究專案至多一筆 PENDING、RUNNING 或 SUCCEEDED。 | ✅ | Integration | □ |
| AC-961-1 | 資料庫 V19：分流、SCR、拆解、交付表與自癒視圖的不可變與 CHECK（Flyway V19） | AT-961-1-4 | research_route_steps 的 CHECK 與主鍵：十一個步驟名、五個狀態、步序下界、(route_id, step_no) 唯一。 | ✅ | Integration | □ |
| AC-961-1 | 資料庫 V19：分流、SCR、拆解、交付表與自癒視圖的不可變與 CHECK（Flyway V19） | AT-961-1-5 | research_scr 的 CHECK 與唯一鍵：型別、來源類別、理由分類、狀態列舉與 (research_id, scr_no) 唯一。 | ✅ | Integration | □ |
| AC-961-1 | 資料庫 V19：分流、SCR、拆解、交付表與自癒視圖的不可變與 CHECK（Flyway V19） | AT-961-1-6 | research_decompositions 的 CHECK：路徑、雜湊格式、任務數下界、七個狀態。 | ✅ | Integration | □ |
| AC-961-1 | 資料庫 V19：分流、SCR、拆解、交付表與自癒視圖的不可變與 CHECK（Flyway V19） | AT-961-1-7 | research_deliveries：列舉、雜湊格式、(research_id, kind, ref) 唯一、append-only（P2 寫入，表於 P1 建立）。 | ✅ | Integration | □ |
| AC-961-1 | 資料庫 V19：分流、SCR、拆解、交付表與自癒視圖的不可變與 CHECK（Flyway V19） | AT-961-1-8 | 四張 V19 受控可更新表的通用守衛：清單內欄可更新、清單外欄位與任何 DELETE 被拒；含複合主鍵表的列定位（與 V16 函式內的允許清單逐表對拍；不併入 P0 的受控表迴圈）。 | ✅ | Integration | □ |
| AC-961-1 | 資料庫 V19：分流、SCR、拆解、交付表與自癒視圖的不可變與 CHECK（Flyway V19） | AT-961-1-9 | 視圖 v_research_healing_attempts：只含 RETRYING 與 FAILED 步驟、經 console_project_id 連結、不提供任何寫入路徑。 | ✅ | Integration | □ |
| AC-961-1 | 資料庫 V19：分流、SCR、拆解、交付表與自癒視圖的不可變與 CHECK（Flyway V19） | AT-961-1-E-1 | 所有十八張 research_ 表（P0 十三張加 V19 五張）逐表 DELETE 一律被擋，守衛錯誤的 SQLSTATE 一律為類別 23。 | ✅ | Integration | □ |
| AC-961-1 | 資料庫 V19：分流、SCR、拆解、交付表與自癒視圖的不可變與 CHECK（Flyway V19） | AT-961-1-E-2 | 既有五個 Flyway IT 的版本清單改為 1 至 19，且 BackupJobMigrationIT 的「既有表零變動」快照把視圖排除。 | ✅ | Integration | □ |
| AC-961-1 | 資料庫 V19：分流、SCR、拆解、交付表與自癒視圖的不可變與 CHECK（Flyway V19） | AT-961-1-E-3 | V19 的預設值與 JSONB 欄位型別：published_docs 預設 {}、impl_fsm_actions 預設 []、型別皆為 jsonb。 | ✅ | Integration | □ |
| AC-961-2 | 分流輸入閘與消毒（Bridge route 驗證層） | AT-961-2-1 | 分流請求本文的欄位驗證表：軌道、分支名、庫名、可見性、確認名、範本、理由長度的界內與界外，違規逐欄列出。 | ✅ | Unit | □ |
| AC-961-2 | 分流輸入閘與消毒（Bridge route 驗證層） | AT-961-2-2 | 消毒鏈：黑名單字元、`..`、逃出 allowlist 根的導出路徑、符號連結逃逸、不合 git ref 規則的分支名，一律 422 逐欄列出且零副作用（路徑由 Bridge 導出，使用者不輸入絕對路徑，D-106）。 | ✅ | Integration | □ |
| AC-961-2 | 分流輸入閘與消毒（Bridge route 驗證層） | AT-961-2-3 | 落點目標清單為 Bridge 常數 PLACEMENT_TARGETS（四值，每值附一句出處）：目標模組只能從清單選、預設值取自 PRD 落點表解析結果、覆寫被記錄；不提供 ADMIN 維護（D-100）。 | ✅ | Integration | □ |
| AC-961-2 | 分流輸入閘與消毒（Bridge route 驗證層） | AT-961-2-4 | 分流軌道與 PRD target_scope 不同時必填一句理由（1 至 200 字）並回差異警示；相同時不需要；PRD 凍結檔位元組不變。 | ✅ | Integration | □ |
| AC-961-2 | 分流輸入閘與消毒（Bridge route 驗證層） | AT-961-2-5 | 範本登記制：scaffold_templates 取自目錄清單，選不存在的範本回 422，node 與 java 不在清單。 | ✅ | Integration | □ |
| AC-961-2 | 分流輸入閘與消毒（Bridge route 驗證層） | AT-961-2-6 | Public 需名稱確認：預設 PRIVATE；PUBLIC 缺確認名或不符一律 422 且零副作用；軌道 A 不接受 PUBLIC。 | ✅ | Integration | □ |
| AC-961-2 | 分流輸入閘與消毒（Bridge route 驗證層） | AT-961-2-7 | Gate 0 未完成不得分流：外環 FSM 非 SPEC_FROZEN 或游標不在 route 時，預演與確認一律 409。 | ✅ | Integration | □ |
| AC-961-2 | 分流輸入閘與消毒（Bridge route 驗證層） | AT-961-2-E-1 | 常數邊界一次釘齊：分支名、庫名、理由、確認名、範本變數的界內與界外各一對。 | ✅ | Unit | □ |
| AC-961-3 | 分流預演：動作清單與零副作用、部署不支援 | AT-961-3-1 | 軌道 A 預演動作清單：步驟序固定、每項含動作、目標、是否觸及外部系統，且與執行共用同一份清單。 | ✅ | Integration | □ |
| AC-961-3 | 分流預演：動作清單與零副作用、部署不支援 | AT-961-3-2 | 軌道 B 預演動作清單：含建立目錄、複製並驗證、git init、設 remote、範本檔、初始 commit 與（選 GitHub 時）建遠端與推送，外部系統標示正確。 | ✅ | Integration | □ |
| AC-961-3 | 分流預演：動作清單與零副作用、部署不支援 | AT-961-3-3 | 軌道 A 預演零副作用：主工作樹、worktree 清單、分支清單、目標目錄與資料庫在預演前後逐項相同。 | ✅ | Integration | □ |
| AC-961-3 | 分流預演：動作清單與零副作用、部署不支援 | AT-961-3-4 | 軌道 B 預演零副作用：目標根下不產生任何檔案或目錄，假 gh 只可能收到唯讀探測。 | ✅ | Integration | □ |
| AC-961-3 | 分流預演：動作清單與零副作用、部署不支援 | AT-961-3-5 | 部署不支援：缺 gh、缺可寫 repo 或未設 BRIDGE_SCAFFOLD_ROOT 時預演回 route_unsupported_in_deployment 並指出缺項，零副作用。 | ✅ | Integration | □ |
| AC-961-3 | 分流預演：動作清單與零副作用、部署不支援 | AT-961-3-6 | 目標目錄已存在且非空：預演與確認都回 422 target_not_empty，不覆寫、不合併；存在但為空允許。 | ✅ | Integration | □ |
| AC-961-3 | 分流預演：動作清單與零副作用、部署不支援 | AT-961-3-7 | 分支已存在：預演即回 409 branch_exists，零變更（含 worktree 清單）。 | ✅ | Integration | □ |
| AC-961-3 | 分流預演：動作清單與零副作用、部署不支援 | AT-961-3-E-1 | 預演與執行共用同一份計畫函式：動作清單的步驟名序列恆等於執行的步驟序列，且兩條路徑呼叫同一個驗證函式。 | ✅ | Unit | □ |
| AC-961-4 | 分流執行：逐步入庫、失敗停點、重試、衝突與事件 | AT-961-4-1 | 執行成功路徑（同步）：步驟逐步入庫、成功才寫 route_decision.json 並推進游標到 build／ROUTED，並發出 research.route 事件。 | ✅ | Integration | □ |
| AC-961-4 | 分流執行：逐步入庫、失敗停點、重試、衝突與事件 | AT-961-4-2 | 部分失敗：第 k 步失敗即停，後續步驟不執行，已入庫列保留，游標停在 route 並帶失敗原因。 | ✅ | Integration | □ |
| AC-961-4 | 分流執行：逐步入庫、失敗停點、重試、衝突與事件 | AT-961-4-3 | 重試失敗步驟：已成功的步驟不重做且其列位元組不變，只從失敗步驟起續做。 | ✅ | Integration | □ |
| AC-961-4 | 分流執行：逐步入庫、失敗停點、重試、衝突與事件 | AT-961-4-4 | 失敗不補償到破壞態：Bridge 在失敗後不執行 git clean、stash、刪目錄或刪分支，已建立的 worktree 與分支原地保留。 | ✅ | Integration | □ |
| AC-961-4 | 分流執行：逐步入庫、失敗停點、重試、衝突與事件 | AT-961-4-5 | 同專案不得有第二個進行中的分流：已有 PENDING、RUNNING 或 SUCCEEDED 時 POST route 回 409 route_conflict，零副作用。 | ✅ | Integration | □ |
| AC-961-4 | 分流執行：逐步入庫、失敗停點、重試、衝突與事件 | AT-961-4-6 | 兩個 ADMIN 並發確認同一專案：一個 200、一個 409，只有一筆路由列，副作用只發生一次。 | ✅ | Integration | □ |
| AC-961-4 | 分流執行：逐步入庫、失敗停點、重試、衝突與事件 | AT-961-4-7 | 步驟列先於副作用寫入（DB 先於檔案與子行程）：行程在副作用之後被中斷，重啟時孤兒回收把卡在 RUNNING 的分流列標 FAILED 並可重試。 | ✅ | Integration | □ |
| AC-961-4 | 分流執行：逐步入庫、失敗停點、重試、衝突與事件 | AT-961-4-8 | 權杖與角色：確認需 Bridge 寫入權杖；approver 取自 console-api 轉入的 JWT subject，保留字與格式不合一律 422。 | ✅ | Integration | □ |
| AC-961-4 | 分流執行：逐步入庫、失敗停點、重試、衝突與事件 | AT-961-4-9 | 補償通知：console-api 補償完 Console 專案列後呼叫 :route-compensated，Bridge 驗該列為 FAILED 才改 COMPENSATED（Bridge 為研究表唯一寫入者，D-112）。 | ✅ | Integration | □ |
| AC-961-4 | 分流執行：逐步入庫、失敗停點、重試、衝突與事件 | AT-961-4-E-1 | DB 阻塞時的游標校正（D-128，oracle 取 P0 原文）：阻塞期間游標不重新衍生，復原後 outbox 重放完成的同一交易重新衍生游標。 | ✅ | Integration | □ |
| AC-961-4 | 分流執行：逐步入庫、失敗停點、重試、衝突與事件 | AT-961-4-E-2 | 牆鐘上限邊界（BRIDGE_ROUTE_TIMEOUT_SECONDS＝300；D-105）：299 秒仍執行、300 秒觸發逾時、301 秒不再接受後續步驟。 | ✅ | Unit | □ |
| AC-961-4 | 分流執行：逐步入庫、失敗停點、重試、衝突與事件 | AT-961-4-E-3 | 牆鐘逾時的負控：未逾時的長流程不誤殺，逾時後已成功步驟與其副作用原地保留。 | ✅ | Integration | □ |
| AC-961-5 | 軌道 A：獨立 worktree、發佈、落點 stub 與主工作樹零擾動 | AT-961-5-1 | 於獨立 worktree 建立 feature/issue-<NNNN>：基底 ref 預設 main，主工作樹 HEAD、狀態與 index 前後相同。 | ✅ | Integration | □ |
| AC-961-5 | 軌道 A：獨立 worktree、發佈、落點 stub 與主工作樹零擾動 | AT-961-5-2 | 分支已存在回 409 且零變更；基底 ref 不存在使 GIT_SWITCH 失敗，後續發佈與綁定不執行，可重試。 | ✅ | Integration | □ |
| AC-961-5 | 軌道 A：獨立 worktree、發佈、落點 stub 與主工作樹零擾動 | AT-961-5-3 | 發佈 PRD：位元組相同的複本到目標落點，其 sha256 等於 Gate 0 凍結摘要對應項，feature 分支上有一筆繁體中文 commit。 | ✅ | Integration | □ |
| AC-961-5 | 軌道 A：獨立 worktree、發佈、落點 stub 與主工作樹零擾動 | AT-961-5-4 | 分支變更只含 PRD 發佈檔與落點 stub：根 CLAUDE.md、.claude、落點 SSOT 與 tools 零變更（D-101）。 | ✅ | Integration | □ |
| AC-961-5 | 軌道 A：獨立 worktree、發佈、落點 stub 與主工作樹零擾動 | AT-961-5-5 | Console 專案綁定回填：Bridge 收到 console_project_id 後寫入路由列與研究專案列，並於游標與事件反映。 | ✅ | Integration | □ |
| AC-961-5 | 軌道 A：獨立 worktree、發佈、落點 stub 與主工作樹零擾動 | AT-961-5-6 | 主工作樹零擾動壓力：主工作樹上有進行中的修改（含衝突標記檔與已暫存刪除）時，分流仍成功且這些修改不被觸碰。 | ✅ | Integration | □ |
| AC-961-5 | 軌道 A：獨立 worktree、發佈、落點 stub 與主工作樹零擾動 | AT-961-5-E-1 | 軌道 A 的檔案發佈在 worktree 內原子完成：發佈中途故障不留半寫檔。 | ✅ | Integration | □ |
| AC-961-6 | 軌道 B：範本展開、工作區複製、git 與 gh、token 零外洩 | AT-961-6-1 | python-fastapi 範本展開的檔案集合與確定性：兩次展開逐檔 sha256 相同，無網路、無 LLM。 | ✅ | Unit | □ |
| AC-961-6 | 軌道 B：範本展開、工作區複製、git 與 gh、token 零外洩 | AT-961-6-2 | 範本變數字元集 [A-Za-z0-9_-] 與輸出路徑必須在新根之下：非法變數與路徑逃逸一律拒絕。 | ✅ | Unit | □ |
| AC-961-6 | 軌道 B：範本展開、工作區複製、git 與 gh、token 零外洩 | AT-961-6-3 | .env.example 只含 <YOUR_…> 佔位符：掃描展開樹不得出現真值樣式。 | ✅ | Unit | □ |
| AC-961-6 | 軌道 B：範本展開、工作區複製、git 與 gh、token 零外洩 | AT-961-6-4 | 複製研究工作區：新專案根含 00_research 至 03_execution 完整副本逐檔 sha256 相同，原工作區原地保留。 | ✅ | Integration | □ |
| AC-961-6 | 軌道 B：範本展開、工作區複製、git 與 gh、token 零外洩 | AT-961-6-5 | 初始 commit：git ls-files 不含 00_research/raw 與 .env，且等於預演的 will_commit 清單，全域 git config 不被改動。 | ✅ | Integration | □ |
| AC-961-6 | 軌道 B：範本展開、工作區複製、git 與 gh、token 零外洩 | AT-961-6-6 | gh 建遠端：argv 精確、可見性旗標正確、GH_TOKEN 只進 gh 子行程環境。 | ✅ | Integration | □ |
| AC-961-6 | 軌道 B：範本展開、工作區複製、git 與 gh、token 零外洩 | AT-961-6-7 | token 零外洩：含假 token 的夾具下，日誌、資料庫、HTTP 回應、argv 紀錄、稽核與步驟尾端文字皆零命中。 | ✅ | Integration | □ |
| AC-961-6 | 軌道 B：範本展開、工作區複製、git 與 gh、token 零外洩 | AT-961-6-8 | gh 失敗路徑：token 缺失、權限不足、gh 不存在時該步失敗並顯示原因，本地步驟結果保留，重試只重做遠端步驟。 | ✅ | Integration | □ |
| AC-961-6 | 軌道 B：範本展開、工作區複製、git 與 gh、token 零外洩 | AT-961-6-9 | 範本的最小 pytest 在展開後的新專案內可跑並通過（供既有 evaluator 綁定）。 | ✅ | Integration | □ |
| AC-961-6 | 軌道 B：範本展開、工作區複製、git 與 gh、token 零外洩 | AT-961-6-E-1 | scaffold 根約束：目標不在 BRIDGE_SCAFFOLD_ROOT 之下或根未設，一律拒絕。 | ✅ | Integration | □ |
| AC-961-6 | 軌道 B：範本展開、工作區複製、git 與 gh、token 零外洩 | AT-961-6-E-2 | token 脫敏函式的邊界：遮罩涵蓋 gh 常見 token 前綴、多行輸出、尾端截斷後仍不洩漏。 | ✅ | Unit | □ |
| AC-961-7 | 內環鍵建立與 Stage-1 基線採納（FSM 序列） | AT-961-7-1 | 採納序列：show 建檔、五次 transition、spec-frozen --stage Stage-1，真 CLI 於暫存狀態目錄實跑，終態 SPEC_FROZEN。 | ✅ | Integration | □ |
| AC-961-7 | 內環鍵建立與 Stage-1 基線採納（FSM 序列） | AT-961-7-2 | 逐字證據：內環 Stage-1 的 PRD 摘要等於外環 Gate 0 凍結摘要對應項，root 為目標根。 | ✅ | Integration | □ |
| AC-961-7 | 內環鍵建立與 Stage-1 基線採納（FSM 序列） | AT-961-7-3 | impl_fsm_project 與 impl_state_dir 入庫：鍵名文法、狀態目錄在 allowed roots 且為 build/reports/fsm。 | ✅ | Integration | □ |
| AC-961-7 | 內環鍵建立與 Stage-1 基線採納（FSM 序列） | AT-961-7-4 | 內環鍵已存在或採納中斷：續做以 show 現態為憑，不重做已完成的 transition；建檔前鍵檔已存在且現態不合法回 409。 | ✅ | Integration | □ |
| AC-961-7 | 內環鍵建立與 Stage-1 基線採納（FSM 序列） | AT-961-7-5 | HUMAN_PENDING 採納值只在內環鍵、現態 SCG_VALIDATION 且 reason 以 baseline adoption 起頭時被放行（既有檢查函式不被繞過）。 | ✅ | Unit | □ |
| AC-961-7 | 內環鍵建立與 Stage-1 基線採納（FSM 序列） | AT-961-7-6 | FSM 子行程環境：白名單重建、內環鍵沿既有行為不強制關閉自動恢復，外環鍵仍固定關閉。 | ✅ | Integration | □ |
| AC-961-7 | 內環鍵建立與 Stage-1 基線採納（FSM 序列） | AT-961-7-7 | 第二個理由前綴 tcs gate（D-97）：只在內環鍵、現態 SCG_VALIDATION 且該鍵已有 Stage-1 凍結時放行 transition --to HUMAN_PENDING，動詞集合不變。 | ✅ | Unit | □ |
| AC-961-7 | 內環鍵建立與 Stage-1 基線採納（FSM 序列） | AT-961-7-E-1 | 外環鍵於分流後不被改動：停在 SPEC_FROZEN，狀態檔位元組不變，FSM 呼叫紀錄對外環鍵只有唯讀的 show。 | ✅ | Integration | □ |
| AC-961-7 | 內環鍵建立與 Stage-1 基線採納（FSM 序列） | AT-961-7-E-2 | 採納序列的計數釘住：恰 1 次 show、5 次 transition、1 次 spec-frozen，且沒有 gate、resume 類動詞。 | ✅ | Integration | □ |
| AC-961-8 | gitops 白名單、能力登記與 FSM 單一寫入面（AST 與表驅動鎖） | AT-961-8-1 | gitops 允許集合表驅動：每個 P1 允許形態通過驗證，組出的 argv 為陣列且不經 shell。 | ✅ | Unit | □ |
| AC-961-8 | gitops 白名單、能力登記與 FSM 單一寫入面（AST 與表驅動鎖） | AT-961-8-2 | 禁止形態逐一被拒：強推、硬重設、clean、stash、檢出路徑、restore 路徑、switch -f、全域與系統層 config。 | ✅ | Unit | □ |
| AC-961-8 | gitops 白名單、能力登記與 FSM 單一寫入面（AST 與表驅動鎖） | AT-961-8-3 | 使用者可影響的 argv 片段先過列舉或正規式：選項注入與 shell 元字元一律拒絕。 | ✅ | Unit | □ |
| AC-961-8 | gitops 白名單、能力登記與 FSM 單一寫入面（AST 與表驅動鎖） | AT-961-8-4 | 子行程形態：argv 陣列、shell 為假、環境白名單重建、經 popen_platform_kwargs，且不寫入使用者家目錄設定。 | ✅ | Integration | □ |
| AC-961-8 | gitops 白名單、能力登記與 FSM 單一寫入面（AST 與表驅動鎖） | AT-961-8-5 | 能力登記：git 與 gh 子行程只住 gitops；新模組先登記 CAPABILITY 與 EXEC_MODULES，未登記即紅。 | ✅ | Contract | □ |
| AC-961-8 | gitops 白名單、能力登記與 FSM 單一寫入面（AST 與表驅動鎖） | AT-961-8-6 | FSM 單一寫入面不被破壞：新模組不含 tools.fsm_runtime、字面值 spec-frozen 與 spec-refreeze；create_key 呼叫者集合含 :route 路徑。 | ✅ | Contract | □ |
| AC-961-8 | gitops 白名單、能力登記與 FSM 單一寫入面（AST 與表驅動鎖） | AT-961-8-7 | 白名單範圍不變：RESEARCH_VERBS 集合與既有 ALLOWED_VERBS 不變，resume-from-escalation 仍不入。 | ✅ | Unit | □ |
| AC-961-8 | gitops 白名單、能力登記與 FSM 單一寫入面（AST 與表驅動鎖） | AT-961-8-E-1 | git 與 gh 的 stderr、stdout 回傳給呼叫端前先脫敏並截尾，且 gitops 不對外洩漏絕對路徑以外的環境資訊。 | ✅ | Unit | □ |
| AC-961-8 | gitops 白名單、能力登記與 FSM 單一寫入面（AST 與表驅動鎖） | AT-961-8-E-2 | push 目的限定：只准 origin 與已驗證的分支，refspec 不得帶強推前綴。 | ✅ | Unit | □ |
| AC-961-9 | TCS 草擬 stage（tcs-draft） | AT-961-9-1 | tcs-draft 前置：分流 SUCCEEDED、內環鍵 SPEC_FROZEN 且恰有 Stage-1 凍結、已有拆解列（D-110）、無進行中 stage、無 open SCR；任一不成立回 409 並逐條列 unmet。 | ✅ | Integration | □ |
| AC-961-9 | TCS 草擬 stage（tcs-draft） | AT-961-9-2 | tcs-draft 的 stage run：DB 記 TCS_DRAFT、編譯為最小授權的 spec-engineer run、prompt-by-reference。 | ✅ | Integration | □ |
| AC-961-9 | TCS 草擬 stage（tcs-draft） | AT-961-9-3 | TCS 確定性驗證（即 SCG 預檢，D-109）：AT 與凍結 AC 一一對映、AC 全涵蓋、判定指令非空、無機密、檔名合 _freeze 規則，任一不過 stage 失敗且內環鍵留在 SPEC_DRAFTING。 | ✅ | Integration | □ |
| AC-961-9 | TCS 草擬 stage（tcs-draft） | AT-961-9-4 | TCS 發佈與登記：通過後發佈到目標 docs/03_testing/contracts，內環鍵依序 transition 到 SCG_VALIDATION 與 HUMAN_PENDING（理由前綴 tcs gate），游標 TCS_PENDING。 | ✅ | Integration | □ |
| AC-961-9 | TCS 草擬 stage（tcs-draft） | AT-961-9-5 | TCS 凍結仍走既有 :freeze：帶 TCS 時成功並使內環鍵含 Stage-2，不帶 TCS 時仍 422 missing_tcs；Bridge 不自動凍結。 | ✅ | Integration | □ |
| AC-961-9 | TCS 草擬 stage（tcs-draft） | AT-961-9-6 | Stage-2 未凍結時 Bridge 內環鍵現態可被 console-api 讀到且不被 Bridge 自己放行執行（執行閘在 console-api，D-102）。 | ✅ | Integration | □ |
| AC-961-9 | TCS 草擬 stage（tcs-draft） | AT-961-9-7 | mock-only 下 tcs-draft 可跑：劇本含 (tcs-draft, 0)，Docker 全棧以 mock claude 走完草擬。 | ✅ | Integration | □ |
| AC-961-9 | TCS 草擬 stage（tcs-draft） | AT-961-9-E-1 | TCS 草擬不碰已凍結的規格：已發佈 PRD 與 Gate 0 凍結檔位元組不變。 | ✅ | Integration | □ |
| AC-961-9 | TCS 草擬 stage（tcs-draft） | AT-961-9-E-2 | tcs-draft 重試與重拆承接：驗證失敗後再啟動走完成功路徑；重拆產生新拆解列時承接前一列的 tcs_rel_path 與 tcs_sha256（D-110）。 | ✅ | Integration | □ |
| AC-961-10 | 任務拆解：草稿、有界閘、覆蓋對映與 stale | AT-961-10-1 | 觸發拆解（Bridge :decompose，同步 HTTP、非 stage run）：逐 US 呼叫既有拆解服務，covers_ac 由該次呼叫綁定的 AC 清單確定性賦值，產生草稿與 R8 列。 | ✅ | Integration | □ |
| AC-961-10 | 任務拆解：草稿、有界閘、覆蓋對映與 stale | AT-961-10-2 | 三道有界閘：超過 24 步、有環、空 prompt 任一不過回 422 結構化錯誤，不截斷、不自動修剪。 | ✅ | Integration | □ |
| AC-961-10 | 任務拆解：草稿、有界閘、覆蓋對映與 stale | AT-961-10-3 | 覆蓋對映：凍結 PRD 的每個 AC 至少被一個 task 的 covers_ac 涵蓋，未覆蓋者逐一列出，未知 AC 編號被拒。 | ✅ | Unit | □ |
| AC-961-10 | 任務拆解：草稿、有界閘、覆蓋對映與 stale | AT-961-10-4 | 簽核前置：未覆蓋者清零或各有人工豁免才可寫入 SIGNED_OFF；豁免理由 1 至 500 字、各自成筆（D-113 單一寫入時點）。 | ✅ | Integration | □ |
| AC-961-10 | 任務拆解：草稿、有界閘、覆蓋對映與 stale | AT-961-10-5 | stale：PRD 凍結摘要與拆解的 prd_sha256 不符時，拆解標 STALE。 | ✅ | Integration | □ |
| AC-961-10 | 任務拆解：草稿、有界閘、覆蓋對映與 stale | AT-961-10-6 | DB 與檔案逐欄相等：task_decomposition.json 的 sha256 與 R8 列相符，簽核版本的正式 goals 與 tasks 數量相等。 | ✅ | Integration | □ |
| AC-961-10 | 任務拆解：草稿、有界閘、覆蓋對映與 stale | AT-961-10-7 | 重拆＝新版本：已簽核草稿不可變，只有已簽核的最新版為有效。 | ✅ | Integration | □ |
| AC-961-10 | 任務拆解：草稿、有界閘、覆蓋對映與 stale | AT-961-10-8 | 按 Goal 分批拆解：大型 PRD 單次逾 24 步被拒，改按 Goal 分批後每批不超過 24 步、總數可超過 24。 | ✅ | Integration | □ |
| AC-961-10 | 任務拆解：草稿、有界閘、覆蓋對映與 stale | AT-961-10-E-1 | planner 不得繞過人工 signoff：任何拆解路徑都不會產生 signed_off 為真的草稿，也不呼叫 FSM gate 類動詞。 | ✅ | Integration | □ |
| AC-961-11 | 拆解簽核與執行閘（console-api 二次校驗） | AT-961-11-1 | 簽核：OPERATOR 以上對 POST decomposition/signoff 送出，經既有 import／signoff 服務（不走 HTTP 迴圈）落為正式專案、目標、任務並關聯研究專案。 | ✅ | Integration | □ |
| AC-961-11 | 拆解簽核與執行閘（console-api 二次校驗） | AT-961-11-2 | 簽核的角色與輸入：approver 取 JWT subject；憑證無 subject 回 400、VIEWER 403、匿名 401、ADMIN 同 OPERATOR；本文帶 approver 不被採用。 | ✅ | Integration | □ |
| AC-961-11 | 拆解簽核與執行閘（console-api 二次校驗） | AT-961-11-3 | 未簽核草稿啟動執行回 409，execute、resume、restore 三個入口皆二次校驗，前端停用只是體驗。 | ✅ | Integration | □ |
| AC-961-11 | 拆解簽核與執行閘（console-api 二次校驗） | AT-961-11-4 | 拆解 stale 時啟動執行回 409 decomposition_stale（console-api 側只驗 409 與透傳形狀；STALE 的寫入歸 Bridge 側 AT-961-10-5）。 | ✅ | Integration | □ |
| AC-961-11 | 拆解簽核與執行閘（console-api 二次校驗） | AT-961-11-5 | SCR 開啟期間啟動執行回 409 scr_open，內環唯讀。 | ✅ | Integration | □ |
| AC-961-11 | 拆解簽核與執行閘（console-api 二次校驗） | AT-961-11-6 | TCS 未凍結時內環 run 啟動回 409 fsm_state_conflict（D-102：既有啟動服務的單一前置守衛），凍結後放行。 | ✅ | Integration | □ |
| AC-961-11 | 拆解簽核與執行閘（console-api 二次校驗） | AT-961-11-7 | POST decomposition（觸發）：OPERATOR 以上、Bridge 同步呼叫讀逾時 330 秒、422 結構化錯誤逐字透傳，VIEWER 403。 | ✅ | Integration | □ |
| AC-961-11 | 拆解簽核與執行閘（console-api 二次校驗） | AT-961-11-E-1 | 軌道 B 的 Console 專案 execution_path 為新專案根，須在 allowlist 根之下，否則建專案被拒。 | ✅ | Integration | □ |
| AC-961-11 | 拆解簽核與執行閘（console-api 二次校驗） | AT-961-11-E-2 | 回歸：非研究專案的 Console 專案啟動執行完全不受 D-102 前置守衛影響。 | ✅ | Integration | □ |
| AC-961-12 | SCR 後端：發起、輸入閘、上限、MAJOR 與自癒耗盡路徑 | AT-961-12-1 | 發起 MINOR SCR：寫 research_scr 列、停止進行中 run、新的執行回 409 scr_open、凍結 PRD 位元組不變、游標進 SCR_OPEN。 | ✅ | Integration | □ |
| AC-961-12 | SCR 後端：發起、輸入閘、上限、MAJOR 與自癒耗盡路徑 | AT-961-12-2 | SCR 輸入閘：理由、分類、受影響章節三類違規各自成筆，零 research_scr 列、零 FSM 呼叫、游標不變。 | ✅ | Unit | □ |
| AC-961-12 | SCR 後端：發起、輸入閘、上限、MAJOR 與自癒耗盡路徑 | AT-961-12-3 | SCR 開啟而新 Gate 0 尚未完成時，恢復舊 run 回 409 scr_open，內環唯讀。 | ✅ | Integration | □ |
| AC-961-12 | SCR 後端：發起、輸入閘、上限、MAJOR 與自癒耗盡路徑 | AT-961-12-4 | MINOR 上限（D-104 保守計）：同一研究專案內 kind 為 MINOR 且 status 為 OPEN、APPROVED 或 APPLIED 的列已有 2 筆，第 3 次回 409 scr_limit 並要求改 MAJOR。 | ✅ | Integration | □ |
| AC-961-12 | SCR 後端：發起、輸入閘、上限、MAJOR 與自癒耗盡路徑 | AT-961-12-5 | MAJOR SCR：建立新研究專案（parent、slug、新外環鍵），舊專案游標不變，舊內環鍵不動。 | ✅ | Integration | □ |
| AC-961-12 | SCR 後端：發起、輸入閘、上限、MAJOR 與自癒耗盡路徑 | AT-961-12-6 | 來源類別 HEALING_FAILED：只產生 resume-from-escalation 指令與 research_scr 記錄，不呼叫任何 FSM 寫入動詞。 | ✅ | Integration | □ |
| AC-961-12 | SCR 後端：發起、輸入閘、上限、MAJOR 與自癒耗盡路徑 | AT-961-12-7 | 同一專案同時只有一筆 OPEN 的 SCR：已有 OPEN 時再發起回 409 scr_open。 | ✅ | Integration | □ |
| AC-961-12 | SCR 後端：發起、輸入閘、上限、MAJOR 與自癒耗盡路徑 | AT-961-12-E-1 | 發起 SCR 時沒有進行中 run 不是錯誤：:stop 為冪等，SCR 仍成立。 | ✅ | Integration | □ |
| AC-961-12 | SCR 後端：發起、輸入閘、上限、MAJOR 與自癒耗盡路徑 | AT-961-12-E-2 | 發起 MINOR SCR 時外環轉態失敗的補償：SCR 列標 REJECTED、游標還原、錯誤原樣拋出、槽位釋出可再開。 | ✅ | Integration | □ |
| AC-961-13 | SCR MINOR 的 FSM 指令序列與內環現態矩陣 | AT-961-13-1 | MINOR 收尾序列於暫存狀態目錄實跑：外環重走、Gate-0-SCR 核准、內環五步，decision_trace 等於人工等價序列。 | ✅ | Integration | □ |
| AC-961-13 | SCR MINOR 的 FSM 指令序列與內環現態矩陣 | AT-961-13-2 | 內環現態矩陣：IMPLEMENTATION、EXECUTION_EVALUATION、ADVERSARIAL_EVALUATION、PR_REVIEW 直接起跑，SPEC_AUDIT 現態略過第一個 transition。 | ✅ | Integration | □ |
| AC-961-13 | SCR MINOR 的 FSM 指令序列與內環現態矩陣 | AT-961-13-3 | RTM_VERIFY 與 RELEASE_READY 現態：先 gate FAIL 退回 IMPLEMENTATION 再起跑，回傳不是 IMPLEMENTATION 即回報 BLOCKED 不重試。 | ✅ | Integration | □ |
| AC-961-13 | SCR MINOR 的 FSM 指令序列與內環現態矩陣 | AT-961-13-4 | 現態不在矩陣內（含任何 ESCALATION*）回 409 fsm_state_conflict，零 FSM 寫入、不起跑。 | ✅ | Integration | □ |
| AC-961-13 | SCR MINOR 的 FSM 指令序列與內環現態矩陣 | AT-961-13-5 | gate PR_REVIEW FAIL 被判同模式而改走 SPEC_AUDIT 時回報 BLOCKED，不重試。 | ✅ | Integration | □ |
| AC-961-13 | SCR MINOR 的 FSM 指令序列與內環現態矩陣 | AT-961-13-6 | 新版本與舊凍結版：Gate-0-SCR 核准後版本遞增、新增 R6 列，舊凍結版保留可比對，SCR 轉 APPLIED，既有拆解標 STALE。 | ✅ | Integration | □ |
| AC-961-13 | SCR MINOR 的 FSM 指令序列與內環現態矩陣 | AT-961-13-7 | 游標：SCR(MINOR) 發起後在 studio／SCR_OPEN，新 Gate 0 完成並發佈後回 build（Target Scope 變更才回 route）。 | ✅ | Integration | □ |
| AC-961-13 | SCR MINOR 的 FSM 指令序列與內環現態矩陣 | AT-961-13-8 | 發佈順序與失敗：SPEC_AUDIT 之後才發佈；發佈失敗中止序列並記錄到失敗處。 | ✅ | Integration | □ |
| AC-961-13 | SCR MINOR 的 FSM 指令序列與內環現態矩陣 | AT-961-13-9 | spec-refreeze 的參數與子行程環境：--doc 為目標 docs 相對路徑、--root 為目標根、--approver 為 JWT subject。 | ✅ | Integration | □ |
| AC-961-13 | SCR MINOR 的 FSM 指令序列與內環現態矩陣 | AT-961-13-E-1 | 預算重新計：SCR 重走起草後，Gate-0-SCR 核准時四個閘的計數一併歸零。 | ✅ | Integration | □ |
| AC-961-13 | SCR MINOR 的 FSM 指令序列與內環現態矩陣 | AT-961-13-E-2 | 序列中任一步 FSM 非 0 結束即停止：後續不執行，impl_fsm_actions 含失敗步驟。 | ✅ | Integration | □ |
| AC-961-13 | SCR MINOR 的 FSM 指令序列與內環現態矩陣 | AT-961-13-E-3 | 核准即套用失敗不留空窗：apply_minor 失敗時 SCR 停在 APPROVED，回應帶 scr_apply 狀態，ADMIN 以 :scr-apply 重試，重試冪等。 | ✅ | Integration | □ |
| AC-961-14 | console-api 分流端點：預演、確認、先建專案列與補償 | AT-961-14-1 | route/preview：OPERATOR 以上、輸入閘先於 Bridge、Bridge 的缺項 422 逐字透傳。 | ✅ | Integration | □ |
| AC-961-14 | console-api 分流端點：預演、確認、先建專案列與補償 | AT-961-14-2 | route 確認僅 ADMIN：OPERATOR 與 VIEWER 皆 403，Bridge 請求數 0、projects 列 0。 | ✅ | Integration | □ |
| AC-961-14 | console-api 分流端點：預演、確認、先建專案列與補償 | AT-961-14-3 | 先建 projects 列再呼 Bridge：順序可觀察，execution_path 取自預演回應，同 (execution_path, sdd_project) 只能綁一個專案。 | ✅ | Integration | □ |
| AC-961-14 | console-api 分流端點：預演、確認、先建專案列與補償 | AT-961-14-4 | 失敗補償到安全態：projects 列標 ARCHIVED 並留稽核，不自動清理，且 Bridge 請求紀錄不含清理類呼叫。 | ✅ | Integration | □ |
| AC-961-14 | console-api 分流端點：預演、確認、先建專案列與補償 | AT-961-14-5 | route_conflict 先於建專案列：已有 PENDING、RUNNING、SUCCEEDED 的分流回 409，零 projects 寫入。 | ✅ | Integration | □ |
| AC-961-14 | console-api 分流端點：預演、確認、先建專案列與補償 | AT-961-14-6 | GitHub token：取自 system_configs 加密欄，單次請求傳給 Bridge，不入 DTO、回應、日誌、audit_log 與 toString。 | ✅ | Integration | □ |
| AC-961-14 | console-api 分流端點：預演、確認、先建專案列與補償 | AT-961-14-7 | GET route：回 RouteDecisionDto 與 steps，V+ 可讀，無分流時回空而非 404。 | ✅ | Integration | □ |
| AC-961-14 | console-api 分流端點：預演、確認、先建專案列與補償 | AT-961-14-8 | route 與 decomposition 的 Bridge 呼叫讀逾時為 330 秒（Bridge 牆鐘上限 300 秒＋緩衝，D-105），其餘寫入呼叫維持 30 秒；Bridge 牆鐘逾時回 502 route_step_failed 而非 504 的語意。 | ✅ | Integration | □ |
| AC-961-14 | console-api 分流端點：預演、確認、先建專案列與補償 | AT-961-14-E-1 | scopeDiffersReason 在 console-api 先判：軌道與 PRD target_scope 不同而缺理由回 422，相同時不要求。 | ✅ | Integration | □ |
| AC-961-14 | console-api 分流端點：預演、確認、先建專案列與補償 | AT-961-14-E-2 | approver 只取 JWT subject：請求本文帶 approver 不被採信；欄位轉換 camelCase 與 snake_case 完整。 | ✅ | Integration | □ |
| AC-961-15 | console-api SCR、拆解端點、角色矩陣、OpenAPI 與 reason 契約 | AT-961-15-1 | POST scr 與 GET scr：角色、輸入閘、MINOR 與 MAJOR 回應、HEALING_FAILED 的指令回應。 | ✅ | Integration | □ |
| AC-961-15 | console-api SCR、拆解端點、角色矩陣、OpenAPI 與 reason 契約 | AT-961-15-2 | GET decomposition：回 DecompositionDto（IFACE §3.1）：有效拆解、覆蓋、豁免與 stale 旗標，無拆解回 200 null，V+ 可讀。 | ✅ | Integration | □ |
| AC-961-15 | console-api SCR、拆解端點、角色矩陣、OpenAPI 與 reason 契約 | AT-961-15-3 | OpenAPI：P1 新增 6 條路徑與 9 個操作（總數 107 條路徑、124 個操作），operationId 與契約一致，回應碼表補列；數字由實際新增路徑與操作自算。 | ✅ | Contract | □ |
| AC-961-15 | console-api SCR、拆解端點、角色矩陣、OpenAPI 與 reason 契約 | AT-961-15-4 | reason 四處集合相等：P0 的 22 個、P0 未結 R-2 的 4 個、P1 的 9 個（共 35 個），後端常數、前端 RESEARCH_REASONS、契約、Architecture 研究 reason 表、OpenAPI 說明一致。 | ✅ | Contract | □ |
| AC-961-15 | console-api SCR、拆解端點、角色矩陣、OpenAPI 與 reason 契約 | AT-961-15-5 | ArchUnit 字串掃描：console-api 對 research_ 與 V19 表零寫入，新讀配接器只用 JdbcClient 查詢。 | ✅ | Contract | □ |
| AC-961-15 | console-api SCR、拆解端點、角色矩陣、OpenAPI 與 reason 契約 | AT-961-15-6 | 角色矩陣：route 與 scr/apply 僅 ADMIN；route/preview、scr、decomposition、decomposition/signoff 為 OPERATOR 以上；三個 GET 為 VIEWER 以上。 | ✅ | Integration | □ |
| AC-961-15 | console-api SCR、拆解端點、角色矩陣、OpenAPI 與 reason 契約 | AT-961-15-7 | ResearchFlowPolicy 的 P1 衍生規則表驅動：route、TCS 相態直接取游標，build 相態依 Console 專案與 FSM 衍生，SCR_OPEN 原樣取用。 | ✅ | Unit | □ |
| AC-961-15 | console-api SCR、拆解端點、角色矩陣、OpenAPI 與 reason 契約 | AT-961-15-8 | 源頭鎖：P1 的 Bridge 常數（路由步驟名、路由與 SCR 狀態、reason、事件型別）被 console-api 的契約形狀認得。 | ✅ | Contract | □ |
| AC-961-15 | console-api SCR、拆解端點、角色矩陣、OpenAPI 與 reason 契約 | AT-961-15-9 | ResearchProjectDetail 帶唯讀 targetScope（取自 research_projects.target_scope），供預選卡與差異判斷（D-107）。 | ✅ | Integration | □ |
| AC-961-15 | console-api SCR、拆解端點、角色矩陣、OpenAPI 與 reason 契約 | AT-961-15-E-1 | console-api 透傳 Bridge 的結構化錯誤：狀態碼與 reason 與 details 逐字不變，且 POST 不重試。 | ✅ | Integration | □ |
| AC-961-15 | console-api SCR、拆解端點、角色矩陣、OpenAPI 與 reason 契約 | AT-961-15-E-2 | P0 未結 R-1（D-123 歸 API-P1）：404 文案依 details 或路徑區分，allowlist 條目不存在不再寫成研究專案不存在（reason 仍為 research_not_found）。 | ✅ | Integration | □ |
| AC-961-16 | capabilities 能力探針與 UI 停用 | AT-961-16-1 | capabilities 十三鍵不變、值取真：scaffold_root、scaffold_templates、repo_writable 在 P1 取實值；gh_cli.authenticated 維持 NOT-EVALUABLE（D-98）。 | ✅ | Integration | □ |
| AC-961-16 | capabilities 能力探針與 UI 停用 | AT-961-16-2 | /health/deep 的 research 物件鍵集合維持八個，mode 判定不變，P1 值語意更新。 | ✅ | Integration | □ |
| AC-961-16 | capabilities 能力探針與 UI 停用 | AT-961-16-3 | 容器模式：無 gh、repo 唯讀、未設 scaffold 根時 capabilities 如實回報，預演回缺項。 | ✅ | Integration | □ |
| AC-961-16 | capabilities 能力探針與 UI 停用 | AT-961-16-4 | console-api 的 CapabilitiesDto：P1 欄位 camelCase 轉出、快取 30 秒、不透出內部路徑以外的環境資訊。 | ✅ | Integration | □ |
| AC-961-16 | capabilities 能力探針與 UI 停用 | AT-961-16-5 | 前端依 capabilities 缺項停用控件並說明（D-114、IFACE §8.3）：git 缺→預演與確認兩軌皆停用；repoWritable 假→軌道 A 卡；ghCli.ok 假→僅 GitHub 勾選；scaffoldRoot 為 null 或範本空→軌道 B 卡；mock-only→兩軌皆停用。 | ✅ | Unit | □ |
| AC-961-16 | capabilities 能力探針與 UI 停用 | AT-961-16-E-1 | scaffold_templates 的目錄掃描規則：只認合法名稱、含必要檔的目錄；非法或空目錄不列。 | ✅ | Unit | □ |
| AC-961-16 | capabilities 能力探針與 UI 停用 | AT-961-16-E-2 | capabilities 載入失敗時步驟 3 顯示錯誤態，不假裝可用。 | ✅ | Unit | □ |
| AC-961-17 | 前端 RouteDrawer 與步驟 3 面板 | AT-961-17-1 | Gate 0 核准後進入第 3 步：抽屜顯示卡 A、卡 B 與評估維度表，依 PRD target_scope 預選其一，再進入可重開。 | ✅ | Unit | □ |
| AC-961-17 | 前端 RouteDrawer 與步驟 3 面板 | AT-961-17-2 | Gate 0 未完成：步驟 3 顯示阻擋頁並連回步驟 2，無任何寫入控件。 | ✅ | Unit | □ |
| AC-961-17 | 前端 RouteDrawer 與步驟 3 面板 | AT-961-17-3 | 卡 A 欄位：分支名預設 feature/issue-<NNNN>、基底 ref 預設 main、掛載目標下拉取自落點目標清單並附出處。 | ✅ | Unit | □ |
| AC-961-17 | 前端 RouteDrawer 與步驟 3 面板 | AT-961-17-4 | 卡 B 欄位：專案名稱、owner、庫名、範本下拉取自 capabilities、GitHub 設定預設 Private、Public 需輸入庫名確認並顯示公開警告、CI 與 compose 勾選。 | ✅ | Unit | □ |
| AC-961-17 | 前端 RouteDrawer 與步驟 3 面板 | AT-961-17-5 | 預演面板：OPERATOR 可預演，動作清單以純文字渲染並標示外部系統，預演不改任何狀態。 | ✅ | Unit | □ |
| AC-961-17 | 前端 RouteDrawer 與步驟 3 面板 | AT-961-17-6 | 確認僅 ADMIN；差異警示與一句理由必填；VIEWER 全面停用且 title 為權限不足。 | ✅ | Unit | □ |
| AC-961-17 | 前端 RouteDrawer 與步驟 3 面板 | AT-961-17-7 | 逐步進度與失敗重試：執行中顯示進度清單，部分失敗顯示失敗步驟與原因並提供重試，完成後唯讀摘要與前往下一步。 | ✅ | Unit | □ |
| AC-961-17 | 前端 RouteDrawer 與步驟 3 面板 | AT-961-17-8 | 部署不支援的錯誤態：預演 422 route_unsupported_in_deployment 時指出缺項，續做時還原已選卡與參數。 | ✅ | Unit | □ |
| AC-961-17 | 前端 RouteDrawer 與步驟 3 面板 | AT-961-17-E-1 | Public 確認的邊界：差一個字元、大小寫不同、尾端空白、貼上不可見字元皆視為不符。 | ✅ | Unit | □ |
| AC-961-17 | 前端 RouteDrawer 與步驟 3 面板 | AT-961-17-E-2 | 前端分流常數與後端單一來源對拍：分支名與庫名正規式、理由上限、SCR 上限皆與契約字面相等。 | ✅ | Unit | □ |
| AC-961-18 | 前端步驟 4 前半面板：拆解、覆蓋、簽核與 TCS 草擬 | AT-961-18-1 | 拆解面板：空狀態與觸發拆解、草稿樹、覆蓋矩陣與未覆蓋清單。 | ✅ | Unit | □ |
| AC-961-18 | 前端步驟 4 前半面板：拆解、覆蓋、簽核與 TCS 草擬 | AT-961-18-2 | 簽核鈕：未覆蓋者清零或各有一句豁免理由前停用，簽核者為目前使用者，理由 500 字界。 | ✅ | Unit | □ |
| AC-961-18 | 前端步驟 4 前半面板：拆解、覆蓋、簽核與 TCS 草擬 | AT-961-18-3 | stale 狀態：PRD 更新後拆解標過期，顯示說明與重新拆解入口，已簽核後唯讀。 | ✅ | Unit | □ |
| AC-961-18 | 前端步驟 4 前半面板：拆解、覆蓋、簽核與 TCS 草擬 | AT-961-18-4 | TCS 草擬面板：內環鍵已採納才可草擬，顯示草擬中、待凍結、已凍結三態與路徑雜湊，凍結連到既有介面。 | ✅ | Unit | □ |
| AC-961-18 | 前端步驟 4 前半面板：拆解、覆蓋、簽核與 TCS 草擬 | AT-961-18-5 | 到既有 freeze、import、execute 的連結與執行閘說明：未簽核或未凍結時執行連結停用並說明原因。 | ✅ | Unit | □ |
| AC-961-18 | 前端步驟 4 前半面板：拆解、覆蓋、簽核與 TCS 草擬 | AT-961-18-6 | SCR 開啟時本面板的操作停用並說明（與後端 409 scr_open 一致）。 | ✅ | Unit | □ |
| AC-961-18 | 前端步驟 4 前半面板：拆解、覆蓋、簽核與 TCS 草擬 | AT-961-18-7 | Bridge 或 API 不可用時顯示錯誤態與快取，不顯示空白。 | ✅ | Unit | □ |
| AC-961-18 | 前端步驟 4 前半面板：拆解、覆蓋、簽核與 TCS 草擬 | AT-961-18-E-1 | 覆蓋矩陣在大型 PRD 下仍可渲染：200 個 AC 乘 24 個 task 不阻塞互動。 | ✅ | Unit | □ |
| AC-961-19 | 步驟接入、說明三道鎖、端點函式與前端靜態鎖 | AT-961-19-1 | ?step=route 與 ?step=build 不再是占位，?step=deliver 仍為占位；Gate 0 未完成時超前導回。 | ✅ | Unit | □ |
| AC-961-19 | 步驟接入、說明三道鎖、端點函式與前端靜態鎖 | AT-961-19-2 | 說明三道鎖與寫實內容：research-workspace 的第 3、4 步說明寫實，三道鎖綠，計數不變。 | ✅ | Unit | □ |
| AC-961-19 | 步驟接入、說明三道鎖、端點函式與前端靜態鎖 | AT-961-19-3 | researchFlow 狀態表詞彙涵蓋 P1 相態並與 FLOW_PHASE_LABEL 的鍵一致。 | ✅ | Unit | □ |
| AC-961-19 | 步驟接入、說明三道鎖、端點函式與前端靜態鎖 | AT-961-19-4 | FlowStepper 的 route 與 build 步驟狀態：進行中、失敗阻擋、SCR 進行中標示。 | ✅ | Unit | □ |
| AC-961-19 | 步驟接入、說明三道鎖、端點函式與前端靜態鎖 | AT-961-19-5 | 端點函式與型別：新增 9 個函式（總數 118），operationId 與契約一一對應，schema.d.ts 重產含之，型別與契約 DTO 逐欄相符。 | ✅ | Contract | □ |
| AC-961-19 | 步驟接入、說明三道鎖、端點函式與前端靜態鎖 | AT-961-19-6 | 前端靜態鎖遵守：新元件無陰影與漸層、只用設計 token、無手寫 svg、無 emoji、無 outline-none、無 dark:，四區塊名不出現在 app/research。 | ✅ | Unit | □ |
| AC-961-19 | 步驟接入、說明三道鎖、端點函式與前端靜態鎖 | AT-961-19-E-1 | P1 reason 的前端文案表：每個 P1 reason 有中文說明，且不直出伺服器訊息。 | ✅ | Unit | □ |
| AC-961-20 | 對帳：route_decision、task_decomposition 與 SCR 相態 | AT-961-20-1 | route_decision 項：DB 路由決定列與 route_decision.json 的 sha256 對帳，漂移與缺席各判 drift，兩側皆缺席維持 ok 且 present 為假。 | ✅ | Integration | □ |
| AC-961-20 | 對帳：route_decision、task_decomposition 與 SCR 相態 | AT-961-20-2 | task_decomposition 項：DB R8 與 task_decomposition.json 對帳，改檔與缺席判 drift。 | ✅ | Integration | □ |
| AC-961-20 | 對帳：route_decision、task_decomposition 與 SCR 相態 | AT-961-20-3 | fsm_flow_mapping 對映表增列 P1 DB 游標組合（D-121）：只用 DB 游標值，衍生相態不入對映，TCS_PENDING 加 Stage-2 已凍結列為待校正而非 drift。 | ✅ | Unit | □ |
| AC-961-20 | 對帳：route_decision、task_decomposition 與 SCR 相態 | AT-961-20-4 | 分流時點自動對帳：route 成功路徑內恰一筆對帳事件、consistent 為真，失敗路徑不產生。 | ✅ | Integration | □ |
| AC-961-20 | 對帳：route_decision、task_decomposition 與 SCR 相態 | AT-961-20-E-1 | 對帳不修任何一邊：兩個新檢查項在漂移時，呼叫前後檔案與 DB 列（事件除外）逐項相同。 | ✅ | Integration | □ |
| AC-961-20 | 對帳：route_decision、task_decomposition 與 SCR 相態 | AT-961-20-E-2 | 前端對 pending_correction 的判讀（純函式）：第三態不算漂移，仍可被辨識為待校正。 | ✅ | Unit | □ |
| AC-961-20 | 對帳：route_decision、task_decomposition 與 SCR 相態 | AT-961-20-E-3 | console-api 對帳 DTO 與 OpenAPI 說明涵蓋第三態：ReconcileResultDto 的 status 說明含 pending_correction，並原樣透傳。 | ✅ | Contract | □ |
| AC-961-20 | 對帳：route_decision、task_decomposition 與 SCR 相態 | AT-961-20-E-4 | 步驟 4 面板渲染對帳結果：pending_correction 顯示「待校正」說明、不顯示漂移警示橫幅，並提供「重新對帳」入口（元件載具，承接 AT-961-20-E-2 的判讀）。 | ✅ | Unit | □ |
| AC-961-21 | 入庫完整率與稽核列（V19 口徑） | AT-961-21-1 | records/audit 的 V19 口徑：R7、R8 取自路由與拆解表，missing 恰為尚未交付者。 | ✅ | Integration | □ |
| AC-961-21 | 入庫完整率與稽核列（V19 口徑） | AT-961-21-2 | audit_log：ADMIN 確認分流、OPERATOR 簽核拆解各有一列 2xx 寫入審計，並與 R7、R8 同 trace_id 含 digest 與理由。 | ✅ | Integration | □ |
| AC-961-21 | 入庫完整率與稽核列（V19 口徑） | AT-961-21-E-1 | 被拒的分流相關寫入請求亦各有一列審計（V6 過濾器對每個 /api 寫入請求恆一列）。 | ✅ | Integration | □ |
| AC-961-22 | 整合 P1：拋棄式 clone、假 gh、Docker mock 與 Playwright 真棧 | AT-961-22-1 | 整合鏈（軌道 A）：拋棄式 clone 上預演、確認、發佈、內環鍵採納、對帳，主工作樹零擾動，逐字證據。 | ✅ | Integration | □ |
| AC-961-22 | 整合 P1：拋棄式 clone、假 gh、Docker mock 與 Playwright 真棧 | AT-961-22-2 | 整合鏈（軌道 B）：暫存 scaffold 根與假 gh 上走完新專案、複製、初始 commit 與遠端，token 零外洩。 | ✅ | Integration | □ |
| AC-961-22 | 整合 P1：拋棄式 clone、假 gh、Docker mock 與 Playwright 真棧 | AT-961-22-3 | 整合鏈（拆解後 TCS 草擬）：接 22-1，先 :decompose（夾具引擎）再 tcs-draft 以 mock 劇本走完，內環 Stage-2 的 show 逐字證據。 | ✅ | Integration | □ |
| AC-961-22 | 整合 P1：拋棄式 clone、假 gh、Docker mock 與 Playwright 真棧 | AT-961-22-4 | 整合鏈（SCR MINOR）：接 22-3 之後（內環已進入 IMPLEMENTATION 的夾具態），SCR 序列端到端，證據與人工等價序列一致。 | ✅ | Integration | □ |
| AC-961-22 | 整合 P1：拋棄式 clone、假 gh、Docker mock 與 Playwright 真棧 | AT-961-22-5 | Docker 全棧（mock-only）：API 直呼預演回缺項，capabilities 如實，UI 停用兩卡並說明。 | ✅ | E2E | □ |
| AC-961-22 | 整合 P1：拋棄式 clone、假 gh、Docker mock 與 Playwright 真棧 | AT-961-22-6 | Docker 全棧：步驟 4 前半與步驟 5 的呈現——build 顯示拆解面板空狀態與停用的草擬，deliver 仍為占位。 | ✅ | E2E | □ |
| AC-961-22 | 整合 P1：拋棄式 clone、假 gh、Docker mock 與 Playwright 真棧 | AT-961-22-7 | a11y 與版面：RouteDrawer 與 BuildFrontPanel 在 1440、1000、600 寬度無水平溢出且 axe 無 serious 與 critical，抽屜焦點陷阱與歸還正確。 | ✅ | E2E | □ |
| AC-961-22 | 整合 P1：拋棄式 clone、假 gh、Docker mock 與 Playwright 真棧 | AT-961-22-8 | P0 既有 E2E 不退步：兩條 Docker 路徑仍綠，唯一改動為占位斷言的預期值。 | ✅ | E2E | □ |
| AC-961-22 | 整合 P1：拋棄式 clone、假 gh、Docker mock 與 Playwright 真棧 | AT-961-22-E-1 | 假 gh 夾具兩形態可行：本平台的假 gh 可被 gitops 以 PATH 解析並執行，記錄 argv 與環境鍵名。 | ✅ | Integration | □ |
| AC-961-22 | 整合 P1：拋棄式 clone、假 gh、Docker mock 與 Playwright 真棧 | AT-961-22-E-2 | 拋棄式 clone 的兩種來源都可：git clone --no-hardlinks 與 git archive 匯出再 git init，分流最小路徑皆通過。 | ✅ | Integration | □ |
| AC-961-23 | 邊界、跨平台與衛生閘（允許變更集合、禁區、無新守衛、無新目錄項原語） | AT-961-23-1 | 允許變更檔案集合與禁區：只動各包 §5.7 的集合，禁區零差異。 | ✅ | Gate | □ |
| AC-961-23 | 邊界、跨平台與衛生閘（允許變更集合、禁區、無新守衛、無新目錄項原語） | AT-961-23-2 | 不新增 os.replace、rename、move 站點：研究套件的目錄項原語站點數不增，根層 dirent 鎖綠。 | ✅ | Gate | □ |
| AC-961-23 | 邊界、跨平台與衛生閘（允許變更集合、禁區、無新守衛、無新目錄項原語） | AT-961-23-3 | 不新增 hook、守衛碼與根層 tools 模組。 | ✅ | Gate | □ |
| AC-961-23 | 邊界、跨平台與衛生閘（允許變更集合、禁區、無新守衛、無新目錄項原語） | AT-961-23-4 | 新 Python 衛生：encoding 宣告、時間戳帶時區、平台專屬 API 罩 sys.platform、ruff 兩視角 0 錯、LF。 | ✅ | Gate | □ |
| AC-961-23 | 邊界、跨平台與衛生閘（允許變更集合、禁區、無新守衛、無新目錄項原語） | AT-961-23-5 | Bridge 全套與跨平台守衛：含新模組後全套綠且 0 skipped（DSN 與 SDD_ROOT 在場）。 | ✅ | Integration | □ |
| AC-961-23 | 邊界、跨平台與衛生閘（允許變更集合、禁區、無新守衛、無新目錄項原語） | AT-961-23-E-1 | hermetic：AT 全程不連外部網路，假 gh 與假連線層取代真端點。 | ✅ | Integration | □ |
| AC-961-24 | 文件連動、追溯與 V 系列 | AT-961-24-1 | 文件閘與追溯：新文件無測試摘要字樣加四位數字同行、RTM 每列回填、編號不撞號、Architecture 5.4 檢查表逐項有交付。 | ✅ | Gate | □ |
| AC-961-25 | TCS 凍結後的游標校正（D-125）：讀端衍生、Bridge 對帳校正、凍結後觸發與重新對帳 | AT-961-25-1 | 讀端衍生（D-125 之一）：flowPhase 為 TCS_PENDING 且內環 FSM 視圖有 Stage-2 凍結時 effective 回 build／BUILD_READY／IDLE，其餘不變。 | ✅ | Unit | □ |
| AC-961-25 | TCS 凍結後的游標校正（D-125）：讀端衍生、Bridge 對帳校正、凍結後觸發與重新對帳 | AT-961-25-2 | Bridge :reconcile 校正（D-125 之二）：TCS_PENDING 且內環已凍結 Stage-2 時，同交易把游標寫為 build／ROUTED／IDLE 並記 research.step 事件。 | ✅ | Integration | □ |
| AC-961-25 | TCS 凍結後的游標校正（D-125）：讀端衍生、Bridge 對帳校正、凍結後觸發與重新對帳 | AT-961-25-3 | 凍結後觸發（D-125 之三）：既有 SDD freeze 服務成功後，若專案綁研究專案則呼叫 Bridge :reconcile 恰一次，其他情況不呼叫。 | ✅ | Integration | □ |
| AC-961-25 | TCS 凍結後的游標校正（D-125）：讀端衍生、Bridge 對帳校正、凍結後觸發與重新對帳 | AT-961-25-4 | 步驟 4 面板的「重新對帳」：OPERATOR 以上可按、送出一次 reconcile，成功後面板依回應刷新（BUILD_READY）。 | ✅ | Unit | □ |
| AC-961-25 | TCS 凍結後的游標校正（D-125）：讀端衍生、Bridge 對帳校正、凍結後觸發與重新對帳 | AT-961-25-E-1 | 負控：Stage-2 未凍結時不校正、不發事件、不衍生為 BUILD_READY。 | ✅ | Integration | □ |

---
## 2. 可自動化 AT 格式規範

> **徑判定（計畫書 §1 末段）**：Bridge（Python）可走徑①委派迴圈；backend（Java）與 frontend（TS）走徑②「SDD session-only」——**Java 與 TS 的 AT 不入 evaluator**，由 session 內自跑判定指令並**把輸出逐字貼進證據檔與 RTM**（沒貼＝未驗證），並在最終回覆逐 AT 列出 AT 底線形與其測試輸出。Bridge 的 AT 若改走徑①，由主控把 §3.1 的 Given／When／Then 轉成 Gherkin 區塊並加驗收字樣，不改 AT 內容；本檔以 §3 的 Given／When／Then 為規範性文字。
>
> **AT 底線形**＝把 AT ID 的連字號換成底線（`AT-961-3-2` 的底線形是 `AT_961_3_2`；`AT-961-13-E-3` 是 `AT_961_13_E_3`）；每個 AT 的測試函式（Java 為方法）名稱須含其底線形（`test_AT_961_3_2_…`、`AT_961_15_6_roleMatrix…`、vitest 的 `it("AT_961_17_1 …")`）。每個 AC 內數字序與 E 序各不超過 9。**同一 AT 的子情境**以參數化或 `subTest` 實作並保留 AT 底線形，任一子情境失敗時訊息須指出是哪個情境。**AT 內不引用其他 AT 的 ID 作為執行條件**（本檔 AT 文字中的「沿 AT-961-x」「見 AT-961-x」僅為讀者導引，不是測試相依；只有 §1、§6 的表格以 AT ID 作為映射）。
>
> **不得新增 skip、xfail、`it.skip`、`describe.skip`**，唯一例外是下列兩類**有名稱的環境缺件**，且必須以固定字首標示：(a) 框架對拍、真 CLI 與暫存 FSM 實跑缺 `SDD_ROOT`：`pytest.skip("TOOL-ABSENCE: SDD_ROOT 不存在")`；(b) 需要真 PostgreSQL 的 Bridge AT 缺 `BRIDGE_TEST_DSN`：沿 `tests/test_db_integration.py` 體例 `@pytest.mark.db` 加 `skipif`，reason 以 `TOOL-ABSENCE: BRIDGE_TEST_DSN` 起頭；另允許 (c) 平台缺件（無權建立符號連結或 junction）以 `TOOL-ABSENCE: symlink` 標示該子情境。三類在一般開發跑可以存在，但**SCG-4 與 RTM 證據必須在 `SDD_ROOT` 與 `BRIDGE_TEST_DSN` 皆在場下跑到 0 skipped**（符號連結子情境於該平台標「未驗」並寫入證據）；以 skip 充當通過一律不接受。git 或 loopback 埠缺席視為環境壞、直接失敗。
>
> **判定指令的三種形態**（各 AT 末行只列「引數部分」；cwd 如下，PowerShell 不用裸 cd、讀 rc 先存變數再讀）：
>
> - **Bridge（pytest；根 `.venv` 已啟用）**：`python -m pytest tests/<檔> -k <AT 底線形> -q`；DB 型加 `BRIDGE_TEST_DSN`。
> - **backend（Gradle；整合測試需 Docker）**：`gradlew test --tests "<類別全名>.<AT 底線形>*"`。
> - **frontend（vitest；E2E 為 Playwright）**：`npx vitest run <檔> -t <AT 底線形>`；E2E 為 `npx playwright test <檔> -g <AT 底線形>`（Docker 全棧用 `tests/e2e/docker.config.ts`，沿 `tests/e2e/README.md` 既有形態）。

```powershell
Push-Location AgentConsole\engine-bridge; $env:BRIDGE_TEST_DSN='<YOUR_TEST_DSN>'; python -m pytest tests/test_research_route_exec.py -k AT_961_4_1 -q; $rc_py = $LASTEXITCODE; Pop-Location
Push-Location AgentConsole\backend; .\gradlew.bat test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_961_1_2*"; $rc_jv = $LASTEXITCODE; Pop-Location
Push-Location AgentConsole\frontend; npx vitest run components/domain/research/RouteDrawer.test.tsx -t AT_961_17_1; $rc_ts = $LASTEXITCODE; Pop-Location
"pytest rc=$rc_py gradle rc=$rc_jv vitest rc=$rc_ts"
```

```bash
(cd AgentConsole/engine-bridge && . ../../.venv/bin/activate && BRIDGE_TEST_DSN='<YOUR_TEST_DSN>' python -m pytest tests/test_research_route_exec.py -k AT_961_4_1 -q; echo "pytest rc=$?")
(cd AgentConsole/backend && ./gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_961_1_2*"; echo "gradle rc=$?")
(cd AgentConsole/frontend && npx vitest run components/domain/research/RouteDrawer.test.tsx -t AT_961_17_1; echo "vitest rc=$?")
```

> **斷言簡寫與夾具名**（本檔各 AT 共用；實作與設施細節見 §5）：
>
> - **Bridge 側**：`RDB`＝`make_research_db()`（`tests/research_pg_support.py`：在 `BRIDGE_TEST_DSN` 所指伺服器建拋棄式資料庫，依序套用 backend 的 `V1`～`V19` Flyway 檔，交出 DSN，測後 DROP；PKG-DB-P1 把檔數常數與清單改到 19）；`WS`＝`research_root` 夾具；`LB`＝活 Bridge（沿 `tests/conftest.py::make_bridge`，設定含 `db_dsn`、`research_root`、`research_write_token`、`scaffold_root`、`worktree_root`、`repo_root`、`claude.command` 指向 `FC`）；`H`＝標頭 `X-Bridge-Token: <T>`；`FC`＝研究劇本假 claude；`SPEC`＝`SDD_ROOT`（真框架 LATEST，或 `tests/fake_sdd.py` 的替身）；`TMPFSM`＝暫存 FSM 狀態目錄夾具（形態同計畫書附錄 A）；`GIT`＝拋棄式 git 夾具（`tests/research_git_support.py`，§5.2）；`GH`＝假 gh 夾具（`tests/fixtures/research/fake_gh/**`，§5.2）。
> - **backend 側**：`AbstractIntegrationTest`、`AbstractApiIT`（Testcontainers PG18；沿既有類別）；迷你 Bridge＝`MiniBridge`（記錄請求、回放黃金檔；補 route、scr、decompose、route-compensated 端點）；`viewer()`、`operator()`、`admin()` 憑證沿既有 `ApiClient`。
> - **frontend 側**：`Providers` 與 `stubApi`、以既有測試助手注入角色；EventSource 與 fetch 以替身；測試 id 以 `data-testid` 取元素。
> - **E2E**：Docker 全棧只跑 mock claude（nginx 80 埠、`E2E_ROOT` 短路徑、並行各自 `--output`）；Playwright mock spec 以 `mockApi.ts` 體例。

---
## 3. AT 完整清單與 Given／When／Then

> 每個 AT 一條：`AT 編號（測試框架｜測試檔｜類型｜對應 PRD AC）描述`，其下為 Given、When、Then 與判定指令。AC 層級的 Given／When／Then 見 §1.1。**Then 欄中的程式碼字面值一律用反引號；本檔所有數值（上限、字元數、逾時）取自 PRD、ADR、契約與主控裁決，為「初值（未校準）」者實作時亦以常數登記並以測試釘住。**

### 3.1 Bridge（pytest；可走徑①委派迴圈，亦可徑②自跑）

- **AT-961-2-1**（pytest｜`test_research_route_gate.py`｜Unit｜AC-R2P-11-5、AC-R2P-13-3）分流請求本文的欄位驗證表：軌道、分支名、庫名、可見性、確認名、範本、理由長度的界內與界外，違規逐欄列出。
  - Given `route.validate_request(body, caps, research)` 純函式（Bridge `app/research/route.py`）與固定的能力快照（範本清單含 `python-fastapi`）
  - When 逐列餵入：`track` 為 `A`、`B`、`C`、缺；`branch_name` 為 `feature/issue-0007`、`feature/` 加 40 個合法字元、加 41 個、含大寫、含底線、含空白、不以 `feature/` 起頭；`project_name`（軌道 B；內環鍵 `<project-name>`）為 2、62、1、63 字元、含大寫、含 `/` 與反斜線、數字起頭（D-119：`^[a-z][a-z0-9-]{1,61}$`）；`repo_name` 為 2、39、1、40 字元、數字起頭、含大寫、含底線，另一次省略 `repo_name`（預設取 `project_name`）；`owner` 為 1、39、40 字元、以連字號起頭、含底線；`visibility` 為 `PRIVATE`、`PUBLIC`、`private`、缺；`stack_template` 為 `python-fastapi`、`node`、空字串；`ci` 與 `docker_compose` 為布林與字串 `"yes"`；`scope_differs_reason` 為 1、200、201 字元、空字串；請求本文含已退役的 `target_path`（D-106）；一次餵多個違規
  - Then 每個違規回 422 的 `violations[]` 一筆（`field`、`rule`、`message`），多違規各自成筆、順序固定（依請求欄位序）；界內值零違規；`feature/` 加 40 字元通過、41 字元違規（規則 `branch_name_pattern`）；`project_name` 2 與 62 字元通過、1 與 63 字元違規；`repo_name` 明示給值時 2 與 39 字元通過、1 與 40 字元違規，省略時等於 `project_name`；`owner` 取 `^[A-Za-z0-9][A-Za-z0-9-]{0,38}$`；`visibility` 缺省值為 `PRIVATE`；`stack_template` 不在登記清單者違規（規則 `unknown_template`）；`ci` 與 `docker_compose` 非布林違規；`target_path` 一律違規（規則 `retired_field`）；常數取單一來源（§5.1），測試不內嵌第二份數字
  - 判定：python -m pytest tests/test_research_route_gate.py -k AT_961_2_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-2-2**（pytest｜`test_research_route_gate.py`｜Integration｜AC-R2P-11-5）消毒鏈：黑名單字元、`..`、逃出 allowlist 根的導出路徑、符號連結逃逸、不合 git ref 規則的分支名，一律 422 逐欄列出且零副作用（路徑由 Bridge 導出，使用者不輸入絕對路徑，D-106）。
  - Given `LB`；`WS`；暫存 allowed roots；研究專案已 Gate 0（FSM 外環 SPEC_FROZEN）；`BASE_DENY_CHARS` 取自 `AutoClaude/autoclaude/utils/shell_deny_chars.py` 的單一來源（測試以 import 取字元集，不手抄）
  - When 對 route-preview 送：`project_name`（軌道 B）含黑名單每個字元（逐字元參數化）、含 `..`、含 `a/b`、含 `a\\b`；`BRIDGE_WORKTREE_ROOT` 與 `BRIDGE_SCAFFOLD_ROOT` 設到 allowed roots 之外、或根內經符號連結（Windows 無權建立時改用 junction；兩者皆不可建則該子情境標 `TOOL-ABSENCE: symlink`）指向根外；`branch_name` 為 `feature/a..b`、`feature/a@{b`、`feature/a.lock`、`feature/a~b`、`feature/a^b`、`feature/a:b`、`feature/a?b`、`feature/a*b`、`feature/a[b`、`feature/a\\b`；本文帶 `target_path`；每次呼叫前後記下 `git status --porcelain`、目標目錄樹雜湊、DB 列數
  - Then 每個違規回 422（reason `sanitization_failed`；`violations[]` 指出欄位與規則；根設定違規則為 `route_unsupported_in_deployment` 的 `details.missing[item=worktree_root]`）；`git status --porcelain`、目錄樹雜湊與資料庫列數（含 `research_events`）前後逐項相同；`branch_name` 的 git ref 規則違規另標規則 `git_ref`；違規訊息不回顯黑名單字元以外的伺服器路徑資訊
  - 判定：python -m pytest tests/test_research_route_gate.py -k AT_961_2_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-2-3**（pytest｜`test_research_route_gate.py`｜Integration｜AC-R2P-12-3）落點目標清單為 Bridge 常數 PLACEMENT_TARGETS（四值，每值附一句出處）：目標模組只能從清單選、預設值取自 PRD 落點表解析結果、覆寫被記錄；不提供 ADMIN 維護（D-100）。
  - Given `LB`；常數 `PLACEMENT_TARGETS`（`autoclaude`、`agentconsole`、`sdd`、`monorepo`，每項 `rule_source` 為一句取自 `Root_Layout_and_Module_Placement.md` §2 的出處句）；落點表夾具副本（`tests/fixtures/research/placement/`）；一個 Gate 0 後的專案其 PRD 的「模組落點表」指向 `agentconsole`
  - When route-preview 的回應 `targets`；呼叫軌道 A：不帶 `target_module`、帶 `agentconsole`、帶 `autoclaude`（覆寫）、帶 `other`、帶自由文字；讀常數與 V19 `research_route_decisions.target_module` 的 CHECK 列舉
  - Then 清單恰四項且每項含 `module`、`rule_source`（非空）、`default`（僅 PRD 解析出的那一項為真）；常數的四值等於 V19 CHECK 的四個列舉值（擴充＝改 SSOT 與新遷移，D-100；本 AT 不允許清單與 CHECK 分家）；不帶 `target_module` 時採預設 `agentconsole`；覆寫為 `autoclaude` 通過、預演動作清單的 `overridden_default` 為真，確認執行後記入 `02_governance/route_decision.json` 與 `research.route` 事件 payload（即 R7）；`other` 與自由文字回 422（規則 `unknown_target_module`）；沒有任何 ADMIN 寫入清單的端點或設定鍵（掃描：契約與 OpenAPI 無此路徑）
  - 判定：python -m pytest tests/test_research_route_gate.py -k AT_961_2_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-2-4**（pytest｜`test_research_route_gate.py`｜Integration｜AC-R2P-11-4）分流軌道與 PRD target_scope 不同時必填一句理由（1 至 200 字）並回差異警示；相同時不需要；PRD 凍結檔位元組不變。
  - Given `LB`；兩個 Gate 0 後的專案：甲的 `target_scope` 為 `AISDLC_MODULE`、乙為 `STANDALONE_PROJECT`；凍結檔 `PRD-v1.0.0.md` 的位元組雜湊
  - When 甲選軌道 A（相同）：不帶理由；甲選軌道 B（不同）：不帶理由、帶 1 字元、帶 200 字元、帶 201 字元、帶全空白；乙選軌道 A（不同）帶合法理由
  - Then 相同時 200 且 `scope_differs` 為假、不要求理由；不同且缺理由回 422（規則 `scope_differs_reason_required`）；全空白視為缺；1 與 200 字元通過且回應含 `scope_differs: true` 與雙方值（`prd_target_scope`、`route_track`）供 UI 警示；201 字元為 422；確認執行後路由列的 `scope_differs_reason` 為所填；每次呼叫前後 PRD 凍結檔位元組與 `frozen_digests` 不變
  - 判定：python -m pytest tests/test_research_route_gate.py -k AT_961_2_4 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-2-5**（pytest｜`test_research_route_gate.py`｜Integration｜AC-R2P-13-7）範本登記制：scaffold_templates 取自目錄清單，選不存在的範本回 422，node 與 java 不在清單。
  - Given `LB`；`BRIDGE_SCAFFOLD_ROOT` 已設（D-96：無預設，未設＝軌道 B 停用）；`app/research/scaffold_templates/` 的實樹（P1 僅 `python-fastapi`）與一份夾具樹（另含 `node`）；範本內的 `.py` 檔一律以 `.tmpl` 後綴存放（避免被 `app/` 全樹 AST 鎖與 `CAPABILITY` 登記掃到，⚖P1-18）
  - When GET capabilities（`BRIDGE_SCAFFOLD_ROOT` 已設與未設各一次）；route-preview 軌道 B 帶 `python-fastapi`、`node`、`java`、`../python-fastapi`、`PYTHON-FASTAPI`；切換到夾具樹再 GET capabilities；對 `app/research/scaffold_templates/**` 掃描副檔名
  - Then 實樹的 `scaffold_templates` 恰為 `["python-fastapi"]`；後四個範本 id 回 422（規則 `unknown_template`；`../` 與大小寫不同者亦拒，不做正規化）；夾具樹的清單含 `node`（證明清單來自目錄掃描而非常數）；範本 id 另需符合 `[A-Za-z0-9_-]`，含其他字元的目錄不列入清單
  - 判定：python -m pytest tests/test_research_route_gate.py -k AT_961_2_5 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-2-6**（pytest｜`test_research_route_gate.py`｜Integration｜AC-R2P-13-3）Public 需名稱確認：預設 PRIVATE；PUBLIC 缺確認名或不符一律 422 且零副作用；軌道 A 不接受 PUBLIC。
  - Given `LB`；`GH` 假 gh 與其呼叫紀錄；暫存 `BRIDGE_SCAFFOLD_ROOT`
  - When 軌道 B route-preview：不帶 `visibility`；`PUBLIC` 不帶 `confirm_repo_name`；`PUBLIC` 帶不同名、大小寫不同、尾端空白；`PUBLIC` 帶相同名；軌道 A 帶 `PUBLIC`
  - Then 預設值 `PRIVATE`；`PUBLIC` 缺確認或不符回 422 `public_confirmation_required`；相符時通過並於動作清單帶警示字樣「PRD 與證據矩陣將公開」；軌道 A 帶 `PUBLIC` 回 422（規則 `public_requires_track_b`）；全部拒絕情境前後目標根樹雜湊相同、`GH` 呼叫紀錄 0 筆
  - 判定：python -m pytest tests/test_research_route_gate.py -k AT_961_2_6 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-2-7**（pytest｜`test_research_route_gate.py`｜Integration｜AC-R2P-11-1）Gate 0 未完成不得分流：外環 FSM 非 SPEC_FROZEN 或游標不在 route 時，預演與確認一律 409。
  - Given `LB`、TMPFSM；四個專案：外環現態 HUMAN_PENDING、ESCALATION、SPEC_FROZEN 且游標 route／FROZEN、SPEC_FROZEN 且已有 SUCCEEDED 的路由
  - When 各 POST route-preview 與 route
  - Then 前兩者 409 `fsm_state_conflict`（`details.expected_state` 為 SPEC_FROZEN、`details.current_state` 為現態；ESCALATION 時為 `escalated`）；第三者通過；第四者 409 `route_conflict`；每個 409 零寫入（狀態檔位元組、`research_route_decisions` 列數、事件序號皆不變）
  - 判定：python -m pytest tests/test_research_route_gate.py -k AT_961_2_7 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-2-E-1**（pytest｜`test_research_route_gate.py`｜Unit｜AC-R2P-13-3、AC-R2P-11-4）常數邊界一次釘齊：分支名、庫名、理由、確認名、範本變數的界內與界外各一對。
  - Given §5.1 登記的 P1 常數（`BRANCH_PATTERN`、`REPO_NAME_PATTERN`、`OWNER_PATTERN`、`SCOPE_REASON_MAX`＝200、`SCR_REASON_MAX`＝500、`WAIVER_REASON_MAX`＝500、`COMPENSATE_REASON_MAX`＝500、`TEMPLATE_VAR_PATTERN`、`PLACEMENT_TARGETS`）
  - When 對每個常數取恰在界內與恰在界外的值各呼叫一次驗證函式
  - Then 界內通過、界外違規（理由類常數各取 1、500 字元通過、0、501 字元違規）；常數值與 §5.1 表逐一相等（單一來源；改常數而不改表時本 AT 紅）；`SCOPE_REASON_MAX` 與 `SCR_REASON_MAX` 是兩個獨立常數，互不借用
  - 判定：python -m pytest tests/test_research_route_gate.py -k AT_961_2_E_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-3-1**（pytest｜`test_research_route_gate.py`｜Integration｜AC-R2P-11-2、AC-R2P-12-1）軌道 A 預演動作清單：步驟序固定、每項含動作、目標、是否觸及外部系統，且與執行共用同一份清單。
  - Given `LB`；`GIT` 拋棄式 clone（見 §5.2：`git clone --no-hardlinks` 本 repo 或 `git archive` 匯出再 `git init`，測試選其一並記錄於證據）；Gate 0 後的專案；`GH` 假 gh
  - When POST route-preview 軌道 A（預設基底 ref `main`）
  - Then 200 `actions[]` 依序為 `VALIDATE_TARGET`、`GIT_SWITCH`、`PUBLISH_DOCS`、`REGISTER_STUB`、`GIT_COMMIT`、`IMPL_KEY_INIT`、`BASELINE_ADOPT`（不產生 `SKIPPED` 列：只列實際動作）；每項含 `seq`、`action`（小寫動作名，如 `worktree_add`）、`step`（V19 十一個步驟名之一）、`target`、`touches_external`、`detail`；軌道 A 的 `touches_external` 皆為假；`GIT_SWITCH` 的 target 含 `feature/issue-<NNNN>`（NNNN＝`rp_no` 零填四位數）、基底 ref 與 worktree 路徑（在 `BRIDGE_WORKTREE_ROOT` 之下，預設 `<BRIDGE_RESEARCH_ROOT>/_worktrees`，D-95）；回應另含 `prd{version_no, semver, sha256, target_scope, scope_differs}`、`impl_fsm_project`、`impl_state_dir`、`execution_path`（供 console-api 先建專案列用，D-106）、`warnings[]`；`GH` 呼叫紀錄 0 筆
  - 判定：python -m pytest tests/test_research_route_gate.py -k AT_961_3_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-3-2**（pytest｜`test_research_route_gate.py`｜Integration｜AC-R2P-13-1）軌道 B 預演動作清單：含建立目錄、複製並驗證、git init、設 remote、範本檔、初始 commit 與（選 GitHub 時）建遠端與推送，外部系統標示正確。
  - Given `LB`；暫存 `BRIDGE_SCAFFOLD_ROOT`；Gate 0 後的專案；`GH`
  - When POST route-preview 軌道 B（帶 `owner`、`repo_name`、`project_name`、`ci`、`docker_compose`）：一次 `create_github` 為假、一次為真（`visibility` 為 `PRIVATE`）
  - Then `create_github` 為假：`actions[]` 依序為 `VALIDATE_TARGET`、`SCAFFOLD_FILES`、`COPY_WORKSPACE`、`GIT_INIT`、`GIT_COMMIT`、`IMPL_KEY_INIT`、`BASELINE_ADOPT`，`touches_external` 全為假；為真：在 `GIT_COMMIT` 之後多 `GH_REPO_CREATE`，其 `touches_external` 為真、target 為 `<owner>/<repo>`、`detail` 含 `remote add origin` 與推送；回應另含 `expected_tracked_files[]`（預期入初始 commit 的檔案集合，不含 `00_research/raw/**` 與 `.env`；供 AT-961-6-5 對拍）、`execution_path`（`<BRIDGE_SCAFFOLD_ROOT>/<project_name>`）、`impl_state_dir`、`warnings[]`（`PUBLIC` 時含 `public_repo_warning`）；`COPY_WORKSPACE` 的 target 為 `<新專案根>/my-project/<slug>`；清單順序即執行順序（步驟序常數單一來源，⚖P1-19：IFACE §4.3 序與 PRD FR-13 敘述序「複製→git init→產生檔→commit」不同，本檔取 IFACE）
  - 判定：python -m pytest tests/test_research_route_gate.py -k AT_961_3_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-3-3**（pytest｜`test_research_route_gate.py`｜Integration｜AC-R2P-11-2、AC-R2P-12-1）軌道 A 預演零副作用：主工作樹、worktree 清單、分支清單、目標目錄與資料庫在預演前後逐項相同。
  - Given `LB`；`GIT` 拋棄式 clone（主工作樹含一個未提交修改與一個未追蹤檔）；Gate 0 後的專案
  - When 記下 `git status --porcelain`（記錄用的 git 呼叫一律帶環境 `GIT_OPTIONAL_LOCKS=0` 以免刷新 index，與 AT-961-8-4 的環境同源）、`git worktree list --porcelain`、`git branch --list`、`git rev-parse HEAD`、目標目錄列表、全部 `console.research_*` 表與 `projects` 的列數與雜湊（D-108：預演 DB 零變化＝所有 `research_*` 表與 `projects` 零變化；`audit_log` 一列為橫切、不計）；連續 POST route-preview 三次（含一次違規請求）；再記一次
  - Then 兩次記錄逐項完全相同；三次預演無任何寫入（含不寫 `research.route` 事件、不佔 `rp_no`、不建 `research_route_decisions` 列、`projects` 零新列）；未提交修改與未追蹤檔的位元組與 mtime 不變；`.git` 目錄內 `index` 的位元組雜湊不變（記錄動作本身因 `GIT_OPTIONAL_LOCKS=0` 不寫 index）（連 index 重寫也不准）；預演使用 `worktree list` 等唯讀動詞（`gitops` 呼叫紀錄只含白名單內唯讀形態）
  - 判定：python -m pytest tests/test_research_route_gate.py -k AT_961_3_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-3-4**（pytest｜`test_research_route_gate.py`｜Integration｜AC-R2P-11-2、AC-R2P-13-1）軌道 B 預演零副作用：目標根下不產生任何檔案或目錄，假 gh 只可能收到唯讀探測。
  - Given `LB`；暫存 `BRIDGE_SCAFFOLD_ROOT`（空）；`GH` 紀錄清空
  - When POST route-preview 軌道 B（`create_github` 為真）兩次
  - Then `BRIDGE_SCAFFOLD_ROOT` 樹雜湊前後相同（連空目錄也不得建立：預演的「建立目錄」只列清單）；`create_github` 為假時 `GH` 呼叫紀錄 0 筆，為真時只允許 `auth status`（唯讀、D-98）且不含任何 token 值；資料庫列數不變；研究工作區的檔案位元組與 mtime 不變
  - 判定：python -m pytest tests/test_research_route_gate.py -k AT_961_3_4 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-3-5**（pytest｜`test_research_route_gate.py`｜Integration｜AC-R2P-11-6、AC-R2P-13-1）部署不支援：缺 gh、缺可寫 repo 或未設 BRIDGE_SCAFFOLD_ROOT 時預演回 route_unsupported_in_deployment 並指出缺項，零副作用。
  - Given `LB` 以四種環境啟動：容器式（PATH 無 `gh`、repo 唯讀、未設 scaffold 根）；僅缺 `gh`；僅 repo 唯讀；僅未設 scaffold 根
  - When 各 POST route-preview 軌道 A、軌道 B（`create_github` 各真假）
  - Then 不可行組合回 422 `route_unsupported_in_deployment`，`details.missing[]` 為 `[{item, reason}]`，`item` 取 `git`｜`gh`｜`repo_writable`｜`scaffold_root`（`BRIDGE_SCAFFOLD_ROOT` 未設）｜`scaffold_templates`（範本目錄為空）｜`worktree_root`，`create_github` 為真且 `gh auth status` 非 0 時另列 `gh_auth`（D-98）；`scaffold_root` 與 `scaffold_templates` 分開列、不合併（D-122：兩種缺項修法不同），依項名字母序；軌道 A 只受 `git`、`repo_writable`、`worktree_root` 影響；軌道 B 且 `create_github` 為假時不要求 `gh`；每個拒絕前後目錄樹雜湊與 DB 列數相同；回應不假裝成功（不得 200 帶空清單）
  - 判定：python -m pytest tests/test_research_route_gate.py -k AT_961_3_5 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-3-6**（pytest｜`test_research_route_gate.py`｜Integration｜AC-R2P-13-6）目標目錄已存在且非空：預演與確認都回 422 target_not_empty，不覆寫、不合併；存在但為空允許。
  - Given `LB`；暫存 `BRIDGE_SCAFFOLD_ROOT`；三個目標：不存在、存在且空、存在且含一個檔
  - When 各 POST route-preview 與（對第三者）route
  - Then 第一、二者通過；第三者 422 `target_not_empty`，`details.path` 只回相對 `BRIDGE_SCAFFOLD_ROOT` 的路徑（D-117，不洩絕對路徑）；目標內既有檔案位元組與 mtime 不變、未新增任何檔；確認路徑同樣在副作用之前拒絕，`research_route_decisions` 列數不變
  - 判定：python -m pytest tests/test_research_route_gate.py -k AT_961_3_6 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-3-7**（pytest｜`test_research_route_gate.py`｜Integration｜AC-R2P-12-1）分支已存在：預演即回 409 branch_exists，零變更（含 worktree 清單）。
  - Given `LB`；`GIT` 拋棄式 clone 內先建好 `feature/issue-0007`
  - When POST route-preview 軌道 A（分支名取預設與自填同名各一次）
  - Then 409 `branch_exists`（`details.branch`）；`git branch --list`、`git worktree list --porcelain`、`git status --porcelain` 前後相同；另一不存在的分支名通過
  - 判定：python -m pytest tests/test_research_route_gate.py -k AT_961_3_7 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-3-E-1**（pytest｜`test_research_route_gate.py`｜Unit｜AC-R2P-11-2）預演與執行共用同一份計畫函式：動作清單的步驟名序列恆等於執行的步驟序列，且兩條路徑呼叫同一個驗證函式。
  - Given `app/research/route.py` 原始碼；`route.build_plan(request, caps)`
  - When AST 掃描預演處理函式與執行處理函式的呼叫；對軌道 A、B 各組合（`create_github` 真假）比對 `build_plan` 的步驟名與執行器實際執行的步驟名
  - Then 兩條路徑都呼叫 `build_plan` 與 `validate_request`（各恰一處、無第二份驗證）；步驟名序列逐項相等；預演不呼叫任何寫入型函式（`gitops` 的非唯讀動詞、`write_text_atomic`、`ResearchDb` 的寫入方法）
  - 判定：python -m pytest tests/test_research_route_gate.py -k AT_961_3_E_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-4-1**（pytest｜`test_research_route_exec.py`｜Integration｜AC-R2P-11-3）執行成功路徑（同步）：步驟逐步入庫、成功才寫 route_decision.json 並推進游標到 build／ROUTED，並發出 research.route 事件。
  - Given `LB`、`RDB`、TMPFSM；`GIT` 拋棄式 clone；Gate 0 後的專案；ADMIN 權杖與 approver `alice@example.com`
  - When 預演通過後 POST route（同步；牆鐘上限 `BRIDGE_ROUTE_TIMEOUT_SECONDS`＝300，D-105）軌道 A
  - Then 200 `{route_id, status: SUCCEEDED, steps[], impl_fsm_project, impl_state_dir, published_docs, flow}`，`flow` 為 `build`／`ROUTED`／`IDLE`；執行中游標為 `route`／`ROUTING`／`RUNNING`；`research_route_decisions` 恰一列且 `status` 先 `PENDING`（寫列時）後 `RUNNING` 後 `SUCCEEDED`；`research_route_steps` 的 `step_no` 自 1 連續、順序等於預演清單、每列 `status` 為 `OK`、`argv_redacted` 非空、`exit_code` 為 0（純 Bridge 內步驟為 NULL）、`started_at` 與 `finished_at` 帶時區且不早於前一步；全部成功之後才寫入 `02_governance/route_decision.json`（R7：請求參數與動作清單與各步結果；位元組雜湊與 `research_artifacts(kind=ROUTE_DECISION)` 登記相符，版本遞增，D-116）；成功前游標停在 route；`research_events` 的 `research.route` 事件每步至少一筆（`routeId`、`stepNo`、`step`、`status` 四鍵）、seq 連續；`decided_by` 為 JWT subject（approver）；Bridge 於分流時點自動對帳（見 AT-961-20-4）
  - 判定：python -m pytest tests/test_research_route_exec.py -k AT_961_4_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-4-2**（pytest｜`test_research_route_exec.py`｜Integration｜AC-R2P-11-3、AC-R2P-12-5）部分失敗：第 k 步失敗即停，後續步驟不執行，已入庫列保留，游標停在 route 並帶失敗原因。
  - Given `LB`、`RDB`；可注入故障的 `gitops` 替身（在第二步 `GIT_SWITCH` 回非零，基底 ref 不存在）
  - When POST route（軌道 A，基底 ref `no-such-ref`；同步等待回應）
  - Then 502 `route_step_failed`，`details.failure_step` 為 `GIT_SWITCH`、`details.route_id`、`details.steps[]`；路由列 `status` 為 `FAILED`、`failure_step` 為 `GIT_SWITCH`；步驟列：`VALIDATE_TARGET` 為 `OK`、`GIT_SWITCH` 為 `FAILED`（`exit_code` 非 0、`stderr_tail` 非空且去敏）、其後各步驟不產生列（IFACE §4.2：只列實際動作），其後步驟的副作用為零（`PUBLISH_DOCS` 不寫檔、不建內環鍵）；`02_governance/route_decision.json` 不存在；游標為 `route`／`ROUTING`／`FAILED`、`flow_detail` 為 `GIT_SWITCH`（失敗步驟名，D-77 體例）；已入庫的步驟列不被刪除；失敗以 `research.route` 的 `FAILED` 狀態事件表達（不是 `research.alert`）
  - 判定：python -m pytest tests/test_research_route_exec.py -k AT_961_4_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-4-3**（pytest｜`test_research_route_exec.py`｜Integration｜AC-R2P-11-3、AC-R2P-12-5、AC-R2P-13-4）重試失敗步驟：已成功的步驟不重做且其列位元組不變，只從失敗步驟起續做。
  - Given 接 4-2 的失敗狀態；故障已排除（基底 ref 改為存在）；`gitops` 呼叫紀錄；`VALIDATE_TARGET` 步驟列的各欄值
  - When POST route（同一專案，帶 `retry: true`，其餘欄位與首次相同）；另一次輸入已變（`base_ref` 不同）的 `retry: true`
  - Then 輸入雜湊（取自 `02_governance/route_decision.json` 的請求參數）相等時：沿用同一路由列（`id` 相同，`status` 自 `FAILED` 回 `RUNNING` 再 `SUCCEEDED`，受控更新守衛允許）；`VALIDATE_TARGET` 步驟列所有欄位位元組與重試前相同；`gitops` 呼叫紀錄只含失敗步驟及其後各步驟的命令，不含 `VALIDATE_TARGET` 的任何重做；最終步驟序等於預演清單；`failure_step` 於成功後為 NULL；`route_decision.json` 於成功後才出現；輸入不等回 409 `route_conflict`（`details.reason` 為 `inputs_changed`），零寫入（IFACE §4.4）
  - 判定：python -m pytest tests/test_research_route_exec.py -k AT_961_4_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-4-4**（pytest｜`test_research_route_exec.py`｜Integration｜AC-R2P-11-3）失敗不補償到破壞態：Bridge 在失敗後不執行 git clean、stash、刪目錄或刪分支，已建立的 worktree 與分支原地保留。
  - Given 接 4-2 但失敗點設在 `PUBLISH_DOCS`（`GIT_SWITCH` 已成功建立 worktree 與分支）；`gitops` 呼叫紀錄
  - When POST route 並輪詢至停止；之後讀 `git worktree list` 與分支清單
  - Then worktree 與 `feature/issue-<NNNN>` 分支仍在；`gitops` 呼叫紀錄不含 `clean`、`stash`、`reset`、`worktree remove`、`branch -D`、`checkout --`；路由列 `status` 為 `FAILED`（`COMPENSATED` 只由 AT-961-4-9 的補償通知寫入）；清理由人工，502 訊息提示人工清理指令（`git worktree remove`）但不代跑
  - 判定：python -m pytest tests/test_research_route_exec.py -k AT_961_4_4 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-4-5**（pytest｜`test_research_route_exec.py`｜Integration｜AC-R2P-11-3）同專案不得有第二個進行中的分流：已有 PENDING、RUNNING 或 SUCCEEDED 時 POST route 回 409 route_conflict，零副作用。
  - Given `LB`、`RDB`；三個專案分別處於路由列 `PENDING`、`RUNNING`、`SUCCEEDED`；另一專案路由列為 `FAILED`
  - When 各 POST route
  - Then 前三者 409 `route_conflict`（`details.route_id`、`details.status`），零寫入（路由列數、步驟列數、事件序號、目標目錄不變）；`FAILED` 的專案可呼叫（視為重試，見 4-3；未帶 `retry` 的第二次完整請求亦回 409 `route_conflict`，須明示 `retry: true`）
  - 判定：python -m pytest tests/test_research_route_exec.py -k AT_961_4_5 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-4-6**（pytest｜`test_research_route_exec.py`｜Integration｜AC-R2P-11-3）兩個 ADMIN 並發確認同一專案：一個 200、一個 409，只有一筆路由列，副作用只發生一次。
  - Given `LB`、`RDB`；`GIT` 拋棄式 clone；兩個執行緒帶不同 approver 同時 POST route
  - When 並發送出
  - Then 恰一個 200、另一個 409 `route_conflict`；`research_route_decisions` 恰一列；`git worktree add` 恰執行一次（`gitops` 呼叫紀錄計數）；部分唯一索引是最後防線（以直接插入第二列驗證 23505，與 AT-961-1-3 互補）
  - 判定：python -m pytest tests/test_research_route_exec.py -k AT_961_4_6 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-4-7**（pytest｜`test_research_route_exec.py`｜Integration｜AC-R2P-11-3）步驟列先於副作用寫入（DB 先於檔案與子行程）：行程在副作用之後被中斷，重啟時孤兒回收把卡在 RUNNING 的分流列標 FAILED 並可重試。
  - Given `LB`、`RDB`；可在指定步驟「子行程已完成但標記完成之前」注入行程中斷的故障點
  - When POST route；於 `GIT_SWITCH` 之後注入中斷；重啟 Bridge（`reap_orphans` 與 `reap_route_orphans`，PACKAGES §4 第 22 列：BR-D1 提供、BR-D2 接線）並重放；再 POST route 帶 `retry: true` 重試
  - Then 中斷前該步驟列已以 `RUNNING` 存在（DB 先於子行程）；重啟回收後該列為 `FAILED`（`stderr_tail` 為 `interrupted`）且路由列為 `FAILED`（不再卡 `RUNNING`，否則部分唯一索引使專案永遠無法重試）；游標為 `route`／`ROUTING`／`FAILED`；重試時 `GIT_SWITCH` 因分支已存在而冪等判定「已完成」（以 `git branch --list` 與 `worktree list` 現查，不重複建立、不回 409 `branch_exists`）並續做後續步驟；不出現「有步驟成功列而副作用不存在」的狀態（⚖P1-6：冪等判定規則為本檔類推）
  - 判定：python -m pytest tests/test_research_route_exec.py -k AT_961_4_7 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-4-8**（pytest｜`test_research_route_exec.py`｜Integration｜AC-R2P-11-3）權杖與角色：確認需 Bridge 寫入權杖；approver 取自 console-api 轉入的 JWT subject，保留字與格式不合一律 422。
  - Given `LB`；缺權杖、錯權杖、正確權杖；approver 為空、`bridge`、`agent`、`system`、101 字元、含空白、`alice@example.com`
  - When 各 POST route-preview 與 route
  - Then 缺或錯權杖 403 `research_write_forbidden`、未設權杖 503 `research_write_disabled`（先中者定案，與 P0 同序）；approver 規則同 Gate 0（長度 1 至 100、`^[A-Za-z0-9._@-]+$`、非保留字）違規 422 `invalid_request`；`bridge.audit` 記錄含 verb（`route`、`route-preview`）、research_id、approver、result、trace_id，且全部回應、日誌與稽核文字不含權杖值
  - 判定：python -m pytest tests/test_research_route_exec.py -k AT_961_4_8 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-4-9**（pytest｜`test_research_route_exec.py`｜Integration｜AC-R2P-11-8）補償通知：console-api 補償完 Console 專案列後呼叫 :route-compensated，Bridge 驗該列為 FAILED 才改 COMPENSATED（Bridge 為研究表唯一寫入者，D-112）。
  - Given `LB`、`RDB`；路由列四種狀態各一個專案（`FAILED`、`RUNNING`、`SUCCEEDED`、已 `COMPENSATED`）、一個不存在的 route_id；寫入權杖；請求 `{route_id, reason, requested_by}`
  - When 各 POST `:route-compensated`
  - Then `FAILED` 列：200 `{route_id, status: COMPENSATED}`、列 `status` 改為 `COMPENSATED`（受控更新守衛允許）、寫一筆 `research.route` 事件（`status` 為 `COMPENSATED`）、`reason` 入事件 payload、游標不動（失敗時已為 `route`／`ROUTING`／`FAILED`）、零 FSM 呼叫與零檔案動作（不 git clean、stash、刪目錄）；其餘三種：409 `route_conflict`（`details.status`）零寫入；不存在的 route_id 404 `research_not_found`；`COMPENSATED` 後新分流＝新 `route_id`（部分唯一索引允許）；缺權杖 403、`reason` 取 1、500 字元通過、空與 501 字元 422（`COMPENSATE_REASON_MAX`）
  - 判定：python -m pytest tests/test_research_route_exec.py -k AT_961_4_9 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-4-E-1**（pytest｜`test_research_route_exec.py`｜Integration｜AC-R2P-11-3）DB 阻塞時的游標校正（D-128，oracle 取 P0 原文）：阻塞期間游標不重新衍生，復原後 outbox 重放完成的同一交易重新衍生游標。
  - Given `LB`、`RDB`；P0 原文行為（PKG-BR-C 交卷：`_chain` 遇 DbBlocked 不排 FAILED、游標 `flow_status` 不重新衍生、BLOCKED_DB run 的游標要等下次 stage 動作才校正；TCS-P0 AT-960-2-5；RTM-P0 同列）；在 route 與 SCR 執行中途關閉資料庫連線使後續寫入失敗；之後恢復資料庫並觸發 outbox 重放兩次
  - When 觀察阻塞期間與重放之後的游標、路由列與 SCR 列、事件序號
  - Then 阻塞期間：stage run 與分流步驟以 outbox 暫存終態、不排 `FAILED`、游標 `flow_status` 不重新衍生（沿 P0），路由列與游標不顯示 `SUCCEEDED`／`build`；P1 校正時點：outbox 重放完成的同一資料庫交易內依 `derive_flow_status` 重新衍生游標（不再等下次 stage 動作），校正後游標與路由列／SCR 列一致、不殘留 `BLOCKED_DB` 標記；事件 seq 連續無缺漏；第二次重放不新增任何列（自然鍵冪等）；P0 的 AT-960-2-5 零改動仍綠（P1 只增「重放完成後游標已校正」的斷言於新 AT）
  - 判定：python -m pytest tests/test_research_route_exec.py -k AT_961_4_E_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-4-E-2**（pytest｜`test_research_route_exec.py`｜Unit｜AC-R2P-11-3）牆鐘上限邊界（BRIDGE_ROUTE_TIMEOUT_SECONDS＝300；D-105）：299 秒仍執行、300 秒觸發逾時、301 秒不再接受後續步驟。
  - Given `LB`、`RDB`；假時鐘；分流夾具讓第 k 步在假時鐘下耗時至指定秒數；設定 `BRIDGE_ROUTE_TIMEOUT_SECONDS` 為 300
  - When 分別讓全流程在假時鐘 299、300、301 秒處仍有步驟待做
  - Then 299 秒：繼續執行；300 秒：回 502 `route_step_failed`（`details.failure_step` 為當下步驟、`details` 含 `reason: route_timeout`）、路由列 `FAILED`、游標 `route`／`ROUTING`／`FAILED`；301 秒：不再啟動任何新步驟（`gitops` 呼叫計數不再增加）；設定值 299 與 301 各驗一次使界線隨設定移動（不是寫死 300）；逾時後可 `retry: true` 續做（沿 AT-961-4-3）
  - 判定：python -m pytest tests/test_research_route_exec.py -k AT_961_4_E_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-4-E-3**（pytest｜`test_research_route_exec.py`｜Integration｜AC-R2P-11-3）牆鐘逾時的負控：未逾時的長流程不誤殺，逾時後已成功步驟與其副作用原地保留。
  - Given 接 4-E-2；一個總耗時 299 秒的成功流程；一個在第 3 步逾時的流程
  - When 各執行並檢查
  - Then 299 秒的流程 200 `SUCCEEDED`；逾時的流程已成功的前兩步列保持 `OK`、其副作用（worktree、分支、發佈檔）仍在、未執行任何 clean、stash、刪目錄（`gitops` 呼叫紀錄）；console-api 讀逾時 330 秒大於 Bridge 牆鐘 300 秒（常數關係釘住：330＞300）
  - 判定：python -m pytest tests/test_research_route_exec.py -k AT_961_4_E_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-5-1**（pytest｜`test_research_route_a.py`｜Integration｜AC-R2P-12-1）於獨立 worktree 建立 feature/issue-<NNNN>：基底 ref 預設 main，主工作樹 HEAD、狀態與 index 前後相同。
  - Given `LB`、`RDB`、TMPFSM；`GIT` 拋棄式 clone（主工作樹有未提交修改、已暫存修改與未追蹤檔各一）；Gate 0 後的專案（`rp_no` 為 7）
  - When POST route 軌道 A（不帶基底 ref；再以另一專案帶 `base_ref` 為 `release-x`）
  - Then 分支名為 `feature/issue-0007`（NNNN＝`rp_no` 零填四位）；`git worktree list --porcelain` 多恰一個 worktree（路徑在 `BRIDGE_WORKTREE_ROOT` 之下，預設 `<BRIDGE_RESEARCH_ROOT>/_worktrees`，D-95）且其 HEAD 等於基底 ref 的提交；主工作樹 `git rev-parse HEAD`、`git status --porcelain`、index 位元組雜湊、未提交與已暫存修改的位元組與 mtime 前後逐項相同；不帶 `base_ref` 時基底為 `main`；帶 `release-x` 時以該 ref 為基底；`gitops` 呼叫紀錄的 worktree 命令恰為 `git -c core.longpaths=true worktree add -b <branch> <path> <base_ref>` 一條（`-c` 為逐次選項、不寫任何 config 檔；除此之外 `-c` 一律被拒），且不含 `checkout`、`switch`、`stash`
  - 判定：python -m pytest tests/test_research_route_a.py -k AT_961_5_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-5-2**（pytest｜`test_research_route_a.py`｜Integration｜AC-R2P-12-1、AC-R2P-12-5）分支已存在回 409 且零變更；基底 ref 不存在使 GIT_SWITCH 失敗，後續發佈與綁定不執行，可重試。
  - Given `LB`、`RDB`；`GIT` 拋棄式 clone；甲：`feature/issue-0007` 已存在；乙：基底 ref 為 `no-such-ref`
  - When 甲 POST route；乙 POST route；乙排除故障後重試
  - Then 甲在確認階段即 409 `branch_exists`，未建路由列、未建 worktree、未寫任何檔；乙路由列 `FAILED`、`failure_step` 為 `GIT_SWITCH`，`PUBLISH_DOCS`、`REGISTER_STUB`、`IMPL_KEY_INIT`、`BASELINE_ADOPT` 皆未執行（目標 `docs/` 無新檔、內環鍵狀態檔不存在、`projects` 列由 console-api 負責，Bridge 不碰），已入庫的 `VALIDATE_TARGET` 列保留；重試成功後序列完整（沿 AT-961-4-3）
  - 判定：python -m pytest tests/test_research_route_a.py -k AT_961_5_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-5-3**（pytest｜`test_research_route_a.py`｜Integration｜AC-R2P-12-2）發佈 PRD：位元組相同的複本到目標落點，其 sha256 等於 Gate 0 凍結摘要對應項，feature 分支上有一筆繁體中文 commit。
  - Given `LB`、`RDB`；`GIT` 拋棄式 clone；Gate 0 後的專案（`frozen_digests` 已知）；目標模組 `agentconsole`
  - When POST route 軌道 A 完成；讀 worktree 內檔案與 `git log`
  - Then worktree 內目標子專案根的 `docs/01_requirements/<slug>_PRD.md`（D-119：slug 原樣、不做大小寫轉換；`target_module` 為 `monorepo` 時為根 `docs/01_requirements/`）存在，其位元組等於研究工作區 `01_specs/PRD-v1.0.0.md`；sha256 等於 `research_gate_decisions.frozen_digests` 對應項（PRD 鍵）且等於路由列 `published_docs` 內登記值；`GIT_COMMIT` 步驟以 `git add -- <明列路徑>`（逐路徑 `check_path`、須在 worktree 內，D-99；軌道 A 禁用 `add -A`）加 `commit -m` 產生恰一筆發佈 commit，訊息為繁體中文並含研究專案 id 與 PRD sha256 前 12 碼；commit 作者由 `GIT_AUTHOR_*` 與 `GIT_COMMITTER_*` 環境設定（全域與本機 git config 檔位元組不變）；發佈檔與凍結摘要不符時該步驟 `FAILED`（`failure_step` 為 `PUBLISH_DOCS`）、不 commit；slug 含數字與連字號時檔名逐字保留（參數化兩個 slug）
  - 判定：python -m pytest tests/test_research_route_a.py -k AT_961_5_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-5-4**（pytest｜`test_research_route_a.py`｜Integration｜AC-R2P-12-6）分支變更只含 PRD 發佈檔與落點 stub：根 CLAUDE.md、.claude、落點 SSOT 與 tools 零變更（D-101）。
  - Given 接 5-3 完成後的 feature 分支與基底 ref
  - When `git diff --name-only <base>..<branch>` 並與期望集合比對
  - Then 變更集合恰為（發佈的 PRD 檔、`<目標子專案根>/docs/02_architecture/Module_Placement_Stub_<slug>.md`；`target_module` 為 `monorepo` 時為根 `docs/02_architecture/` 下同名檔）兩個檔；`CLAUDE.md`、`.claude/**`、`docs/02_architecture/Root_Layout_and_Module_Placement.md`、`tools/**` 皆不在集合內；stub 為固定繁體中文模板：含研究專案 id、PRD sha256、模組名、「請依 Root_Layout §2、§3 手動登記」、檔頭註明「由 ResearchToPRD 產生，非落點 SSOT」，不含任何對 SSOT 的自動編修；各目標模組（autoclaude、agentconsole、sdd、monorepo）參數化各跑一次
  - 判定：python -m pytest tests/test_research_route_a.py -k AT_961_5_4 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-5-5**（pytest｜`test_research_route_a.py`｜Integration｜AC-R2P-12-4）Console 專案綁定回填：Bridge 收到 console_project_id 後寫入路由列與研究專案列，並於游標與事件反映。
  - Given `LB`、`RDB`；請求帶 console-api 先建好的 `console_project_id` 與 `sdd_project`；一個研究專案
  - When POST route 軌道 A 完成；另以不帶 `console_project_id` 的請求呼叫（Bridge 直呼）
  - Then 路由列 `console_project_id` 與 `impl_fsm_project` 為所給值、`research_projects.console_project_id` 同值（皆於同一交易，含一筆 `research.step` 事件）；缺 `console_project_id` 回 422 `invalid_request`（軌道 A 與 B 皆必填：Console 專案先建是 PRD 契約）；`console_project_id` 指向不存在專案回 422（外鍵由 DB 擋、Bridge 轉成結構化錯誤而非 500）
  - 判定：python -m pytest tests/test_research_route_a.py -k AT_961_5_5 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-5-6**（pytest｜`test_research_route_a.py`｜Integration｜AC-R2P-12-1）主工作樹零擾動壓力：主工作樹上有進行中的修改（含衝突標記檔與已暫存刪除）時，分流仍成功且這些修改不被觸碰。
  - Given `GIT` 拋棄式 clone；主工作樹有三種髒狀態：已暫存的新增、未暫存的修改、已暫存的刪除；各記錄位元組與 mtime
  - When POST route 軌道 A 完成；再 POST route 於另一專案（第二個 worktree）
  - Then 兩個 worktree 皆建立；主工作樹的三種髒狀態與 `git status --porcelain` 逐字相同；`git stash list` 為空（Bridge 從未 stash）；主工作樹的目前分支名與 `HEAD` 不變
  - 判定：python -m pytest tests/test_research_route_a.py -k AT_961_5_6 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-5-E-1**（pytest｜`test_research_route_a.py`｜Integration｜AC-R2P-12-5）軌道 A 的檔案發佈在 worktree 內原子完成：發佈中途故障不留半寫檔。
  - Given `LB`；可注入故障的寫檔函式（寫到一半丟錯）
  - When POST route 軌道 A，於 `PUBLISH_DOCS` 注入故障
  - Then worktree 內不存在發佈檔的半寫版本（重用 `fsutil.write_text_atomic` 的暫存檔機制，暫存檔亦被清掉）；步驟 `FAILED`；`app/research/**` 內 `os.replace`、`os.rename`、`shutil.move`、`Path.rename`、`Path.replace` 新增站點為 0（與 AT-961-23-2 同源）
  - 判定：python -m pytest tests/test_research_route_a.py -k AT_961_5_E_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-6-1**（pytest｜`test_research_scaffold.py`｜Unit｜AC-R2P-13-8）python-fastapi 範本展開的檔案集合與確定性：兩次展開逐檔 sha256 相同，無網路、無 LLM。
  - Given `scaffold.expand(template_id, variables, dest)` 與範本目錄 `app/research/scaffold_templates/python-fastapi/`（範本內的 Python 檔以 `.tmpl` 後綴存放、展開時去後綴，⚖P1-18）；變數 `{project_name: demo-app, slug: demo, ...}`；斷網（socket 被替換成拋錯）
  - When 展開兩次到兩個空目錄並逐檔雜湊
  - Then 展開結果含 `README.md`、`.gitignore`（含 `00_research/raw/` 與 `build/reports/` 各一行，後者防內環鍵狀態目錄入版控）、`.github/workflows/` 下至少一個 workflow、`docker-compose.yml`、`.env.example`、`pyproject.toml`、最小 `app/main.py`、至少一個 `tests/test_*.py`（最小 pytest）；展開後的檔案集合不含任何 `.tmpl` 後綴檔；兩次的相對路徑集合與 sha256 完全相同；展開過程零網路連線（假 socket 計數 0）、零子行程；檔案內容不含未代換的 `{{`、`}}` 標記；所有文字檔為 LF 行尾
  - 判定：python -m pytest tests/test_research_scaffold.py -k AT_961_6_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-6-2**（pytest｜`test_research_scaffold.py`｜Unit｜AC-R2P-13-8）範本變數字元集 [A-Za-z0-9_-] 與輸出路徑必須在新根之下：非法變數與路徑逃逸一律拒絕。
  - Given `scaffold.expand` 與 `TEMPLATE_VAR_PATTERN`
  - When 變數值取：恰合法的全字元集；含空白、`.`、`/`、`\\`、`{`、`}`、`$`、`;`、NUL、全形字元的各一；範本內的路徑片段變數為 `..`、`../x`、絕對路徑、經符號連結指向根外（無權建立時標 `TOOL-ABSENCE: symlink`）
  - Then 合法全字元集通過；每個非法值回 `ScaffoldError`（對外映射為 422 `sanitization_failed`）且目的目錄零檔案；輸出檔路徑 `resolve()` 後不在新根之下者一律拒絕且已展開的檔案不殘留（整體先展開到暫存子樹驗證後才落地，或失敗即整樹不存在）
  - 判定：python -m pytest tests/test_research_scaffold.py -k AT_961_6_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-6-3**（pytest｜`test_research_scaffold.py`｜Unit｜AC-R2P-13-8）.env.example 只含 <YOUR_…> 佔位符：掃描展開樹不得出現真值樣式。
  - Given 展開後的新專案樹；真值樣式表（`ghp_`、`github_pat_`、`AKIA`、`sk-`、32 位以上十六進位長串、`BEGIN PRIVATE KEY`）
  - When 對全部展開檔案掃描；解析 `.env.example` 的每個 `KEY=VALUE`
  - Then `.env.example` 的每個值皆為 `<YOUR_…>` 形或空；全樹零真值樣式命中；掃描器有負控（餵含 `ghp_` 假值的樣本時回報命中）且範圍非空（檔案數大於 0）
  - 判定：python -m pytest tests/test_research_scaffold.py -k AT_961_6_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-6-4**（pytest｜`test_research_route_b.py`｜Integration｜AC-R2P-13-2）複製研究工作區：新專案根含 00_research 至 03_execution 完整副本逐檔 sha256 相同，原工作區原地保留。
  - Given `LB`、`RDB`；暫存 `BRIDGE_SCAFFOLD_ROOT`；一個 Gate 0 後的專案（工作區含 `00_research/raw/` 夾具檔）；記下原工作區樹的逐檔 sha256、mtime 與存在性
  - When POST route 軌道 B（`create_github` 為假）完成
  - Then 新專案根 `my-project/<slug>/` 下四個編號目錄的檔案集合與逐檔 sha256 與來源完全相同（含 raw 夾具；D-117：副本含 `00_research/raw/**`、以範本 `.gitignore` 排除入版控，PRD AC-13-2 與 13-5 的措辭差異於 §7 勘誤，見 AT-961-6-5）；步驟 `COPY_WORKSPACE` 先複製後逐檔驗證，驗證不符則步驟 `FAILED`（以故障注入驗：複製後改一個位元組）；原工作區每個檔案的位元組、mtime 與存在性不變、目錄未改名未刪除；無 `os.replace`、`rename`、`move` 呼叫（AST，與 AT-961-23-2 同源）
  - 判定：python -m pytest tests/test_research_route_b.py -k AT_961_6_4 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-6-5**（pytest｜`test_research_route_b.py`｜Integration｜AC-R2P-13-5、AC-R2P-13-2）初始 commit：git ls-files 不含 00_research/raw 與 .env，且等於預演的 will_commit 清單，全域 git config 不被改動。
  - Given 接 6-4，另在工作區放入 `.env` 與 `00_research/raw/x.html`；`HOME` 指到暫存目錄內的空 `.gitconfig`；記下其雜湊
  - When POST route 軌道 B 完成後讀 `git ls-files`、`git log`；與預演的 `will_commit[]` 比對
  - Then 新專案根有 `.git`、恰一筆初始 commit；`git ls-files` 不含 `00_research/raw/**` 與任何 `.env`（`.env.example` 在內）；其集合等於預演 `will_commit[]`；commit 訊息取自模板、不含使用者原文（議題、PRD 內容皆不出現）；作者由 `GIT_AUTHOR_*` 與 `GIT_COMMITTER_*` 環境設定；`HOME` 內 `.gitconfig`、系統層與全域層設定檔位元組前後不變（Bridge 從未執行 `git config --global` 或寫入 `~`）；`.github/workflows/*`、`docker-compose.yml`、`.env.example` 皆在新根且入 commit
  - 判定：python -m pytest tests/test_research_route_b.py -k AT_961_6_5 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-6-6**（pytest｜`test_research_route_b.py`｜Integration｜AC-R2P-13-4、AC-R2P-13-2）gh 建遠端：argv 精確、可見性旗標正確、GH_TOKEN 只進 gh 子行程環境。
  - Given `LB`；`GH` 假 gh（PowerShell 與 POSIX 兩形態，見 §5.2；記錄 argv 與環境變數鍵名單，不記值以外的任何東西——值只存在於夾具的受控記錄，供 6-7 掃描）；`create_github` 為真；請求帶假 token `ghp_FAKE0000000000000000000000000000000000`
  - When POST route 軌道 B（`PRIVATE`）完成；再以 `PUBLIC` 且確認名相符的專案完成
  - Then `GH` 呼叫紀錄含 `auth status`（唯讀）與 `repo create <owner>/<repo> --private --source . --push`（PUBLIC 時為 `--public`）；argv 為陣列、不含 token、不含 shell 串接字元；`GH_TOKEN` 只出現在 gh 子行程的環境（假 gh 記錄環境鍵名單），不出現在 `git` 子行程環境；環境另含 `GIT_TERMINAL_PROMPT=0` 與 `GCM_INTERACTIVE=never`（D-99）；其餘環境鍵為白名單重建（無 `BRIDGE_*`、`SDD_*`、`PYTHONPATH`）；`remote add origin` 由 `git` 子行程執行且 URL 不含 token（不用 `https://<token>@` 形式）；`capabilities.gh_cli.authenticated` 維持 `NOT-EVALUABLE`（D-98：探針不起子行程）
  - 判定：python -m pytest tests/test_research_route_b.py -k AT_961_6_6 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-6-7**（pytest｜`test_research_route_b.py`｜Integration｜AC-R2P-13-4）token 零外洩：含假 token 的夾具下，日誌、資料庫、HTTP 回應、argv 紀錄、稽核與步驟尾端文字皆零命中。
  - Given 接 6-6 的假 token；假 gh 在 stderr 與 stdout 刻意印出該 token（模擬 gh 洩漏）；`LB` 日誌擷取、`bridge.audit` 擷取
  - When POST route 軌道 B 完成（成功與假 gh 失敗兩種）；掃描：全部 HTTP 回應本文、`LB` 日誌檔、`bridge.audit` 行、`research_*` 全部表的全部文字欄與 JSONB 欄（`information_schema` 列舉，不手抄）、研究工作區與新專案根全部檔案、`GH` 與 `git` 的 argv 紀錄、`research_route_steps.argv_redacted`／`stdout_tail`／`stderr_tail`
  - Then 所有掃描面對假 token 字串與其前 8 字元子串皆零命中；步驟尾端的 token 已被替換為遮罩（`***`）；掃描器有負控（在樣本中放入假 token 時回報命中）且範圍非空（表數、欄數、檔數皆大於 0）；token 只存在於單次請求的記憶體與 gh 子行程環境（PRD AC-R2P-13-4）
  - 判定：python -m pytest tests/test_research_route_b.py -k AT_961_6_7 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-6-8**（pytest｜`test_research_route_b.py`｜Integration｜AC-R2P-13-4）gh 失敗路徑：token 缺失、權限不足、gh 不存在時該步失敗並顯示原因，本地步驟結果保留，重試只重做遠端步驟。
  - Given `LB`、`RDB`；`GH` 設為三種行為：無 token 時 `auth status` 非 0；`repo create` 回「權限不足」非 0；PATH 上沒有 gh
  - When POST route 軌道 B（`create_github` 為真）三次；排除故障後重試
  - Then `GH_REPO_CREATE` 步驟 `FAILED`，`stderr_tail` 有人可讀原因（`github_token_missing`、`gh_permission_denied`、`gh_not_found` 之一）且不含 token；`COPY_WORKSPACE`、`GIT_INIT`、`SCAFFOLD_FILES`、`GIT_COMMIT` 的列保持 `OK`、`.git` 與初始 commit 仍在；重試時 `gitops` 呼叫紀錄只含遠端相關命令，不含 `init`、`add`、`commit`，初始 commit 雜湊前後相同；重試成功後路由列 `SUCCEEDED`
  - 判定：python -m pytest tests/test_research_route_b.py -k AT_961_6_8 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-6-9**（pytest｜`test_research_scaffold.py`｜Integration｜AC-R2P-13-8）範本的最小 pytest 在展開後的新專案內可跑並通過（供既有 evaluator 綁定）。
  - Given 展開到暫存目錄的 `python-fastapi` 樹；venv python；斷網
  - When 於該暫存目錄以 `python -m pytest -q` 執行（`-p no:cacheprovider`）
  - Then rc 為 0 且至少執行 1 個測試、0 失敗、0 skipped；測試檔的檔名符合既有 evaluator 對 AT 綁定的 `pytest` 形態（`tests/test_*.py`）；展開樹內不需安裝額外網路相依即可通過（只用標準庫與 `pytest`）；不寫入暫存目錄之外的路徑
  - 判定：python -m pytest tests/test_research_scaffold.py -k AT_961_6_9 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-6-E-1**（pytest｜`test_research_route_b.py`｜Integration｜AC-R2P-13-2）scaffold 根約束：目標不在 BRIDGE_SCAFFOLD_ROOT 之下或根未設，一律拒絕。
  - Given `LB`；兩種設定：scaffold 根已設、未設；目標路徑在根內、根外、根的父層
  - When 各 POST route-preview 與 route 軌道 B
  - Then 根外與父層目標 422 `sanitization_failed`；根未設 422 `route_unsupported_in_deployment`（`details.missing` 含 `scaffold_root`）；根內目標通過；`BRIDGE_SCAFFOLD_ROOT` 自動併入 `BRIDGE_ALLOWED_PATH_ROOTS`（ADR-003 D8），啟動時於 `/health/deep` 揭露
  - 判定：python -m pytest tests/test_research_route_b.py -k AT_961_6_E_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-6-E-2**（pytest｜`test_research_route_b.py`｜Unit｜AC-R2P-13-4）token 脫敏函式的邊界：遮罩涵蓋 gh 常見 token 前綴、多行輸出、尾端截斷後仍不洩漏。
  - Given `redact(text, secrets)` 純函式；輸入：整串 token、token 被換行切開、token 出現在 2000 字元截尾邊界、token 以 URL 編碼形式出現、含多個不同 token
  - When 逐例脫敏後再套 2000 字元尾端截取
  - Then 輸出皆不含 token 原文與其前 8 字元；截尾不會把遮罩切成可還原的半截；未知形態的字串不被誤遮罩（保留可讀診斷）
  - 判定：python -m pytest tests/test_research_route_b.py -k AT_961_6_E_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-7-1**（pytest｜`test_research_adopt.py`｜Integration｜AC-R2P-11-7）採納序列：show 建檔、五次 transition、spec-frozen --stage Stage-1，真 CLI 於暫存狀態目錄實跑，終態 SPEC_FROZEN。
  - Given `SDD_ROOT`（真框架 LATEST；缺則依 §2 TOOL-ABSENCE 規則 skip，SCG-4 須 0 skipped）、TMPFSM；一個已發佈 PRD 的目標根（暫存）；外環 Gate 0 決定列（id 與 sha256 已知）；FSM 呼叫記錄器
  - When 呼叫 `adopt.adopt_baseline(ctx)`
  - Then 呼叫序為 `show`（不帶 `--must-exist`，建檔）、`transition --to SCENARIO_DETECT`、`AGENT_LOAD`、`SPEC_DRAFTING`、`SCG_VALIDATION`、`HUMAN_PENDING`（共五次，`--trigger research_bridge`）、`spec-frozen --stage Stage-1 --doc <已發佈 PRD 相對路徑> --digest --root <目標根> --approver <JWT subject> --reason …`；五次 `--reason` 皆以 `baseline adoption` 起頭並含「SCG 已在外環鍵 <鍵> 通過」與 `gate_decision <id>`；`spec-frozen` 的 `--reason` 含外環決定 id 與 PRD sha256；`show` 後的狀態檔現態為 SPEC_FROZEN、`frozen_stages[-1].stage` 為 `Stage-1`；`decision_trace` 依序為上述轉態；呼叫記錄中 `gate` 動詞為 0 次（D-45：採納不走 gate）
  - 判定：python -m pytest tests/test_research_adopt.py -k AT_961_7_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-7-2**（pytest｜`test_research_adopt.py`｜Integration｜AC-R2P-11-7）逐字證據：內環 Stage-1 的 PRD 摘要等於外環 Gate 0 凍結摘要對應項，root 為目標根。
  - Given 接 7-1；外環 `research_gate_decisions.frozen_digests`
  - When 讀內環 `show` 的 `frozen_stages[-1]`，與外環決定列比對；軌道 A（root＝worktree 內目標子專案根，`--doc` 為已發佈的 `docs/01_requirements/<slug>_PRD.md`）與軌道 B（root＝新專案根，不另發佈，`--doc` 為 `my-project/<slug>/01_specs/PRD-v1.0.0.md`，D-119）各一
  - Then `spec_doc_digests` 內已採納 PRD 的 sha256 與外環 `frozen_digests` 的 PRD 鍵逐位元相同；`--root` 為目標根（不是研究工作區）；`--doc` 為相對目標根的 POSIX 路徑；證據（`show` 全文）逐字貼入整合證據檔（PRD §8.1 P1 出口 (d)）
  - 判定：python -m pytest tests/test_research_adopt.py -k AT_961_7_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-7-3**（pytest｜`test_research_adopt.py`｜Integration｜AC-R2P-11-7）impl_fsm_project 與 impl_state_dir 入庫：鍵名文法、狀態目錄在 allowed roots 且為 build/reports/fsm。
  - Given `LB`、`RDB`；軌道 A（module `agentconsole`、slug `demo`）與軌道 B（專案名 `demo-app`）各一
  - When POST route 完成後讀路由列
  - Then 軌道 A 的 `impl_fsm_project` 為 `agentconsole-demo`（`<module>-<slug>`，module 取 `PLACEMENT_TARGETS`），軌道 B 為 `demo-app`（`<project_name>`）；皆符合內環鍵文法 `^[a-z][a-z0-9-]{1,99}$`（D-119）；`impl_state_dir` 為 `<目標根>/build/reports/fsm` 的絕對路徑、在 allowed roots 之下；兩欄於 `show` 成功後才寫（失敗時為 NULL）；路由列此兩欄的更新屬受控清單內（AT-961-1-8）
  - 判定：python -m pytest tests/test_research_adopt.py -k AT_961_7_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-7-4**（pytest｜`test_research_adopt.py`｜Integration｜AC-R2P-11-7、AC-R2P-11-3）內環鍵已存在或採納中斷：續做以 show 現態為憑，不重做已完成的 transition；建檔前鍵檔已存在且現態不合法回 409。
  - Given TMPFSM 與真 CLI；三種起點：鍵檔不存在；鍵檔已在 SCG_VALIDATION（前三次 transition 已做）；鍵檔已在 SPEC_FROZEN 且 Stage-1 已凍結；另一種：鍵檔存在於 INIT 之外的非採納路徑現態（例如 IMPLEMENTATION）
  - When 各呼叫 `adopt_baseline`
  - Then 不存在：完整序列；SCG_VALIDATION：只補 `transition --to HUMAN_PENDING` 與 `spec-frozen`（呼叫記錄不含前三次 transition 與 `show` 建檔）；已 SPEC_FROZEN 且 Stage-1 已凍結：零 FSM 寫入、冪等成功；非採納路徑現態：回 `fsm_state_conflict`（`details.current_state`）、零寫入，步驟 `FAILED`
  - 判定：python -m pytest tests/test_research_adopt.py -k AT_961_7_4 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-7-5**（pytest｜`test_research_adopt.py`｜Unit｜AC-R2P-11-7）HUMAN_PENDING 採納值只在內環鍵、現態 SCG_VALIDATION 且 reason 以 baseline adoption 起頭時被放行（既有檢查函式不被繞過）。
  - Given `sdd_cli.check_research_allowed` 與 route 模組組出的 argv
  - When 對外環鍵與內環鍵、現態 SCG_VALIDATION 與其他、reason 為 `baseline adoption: x`、`Baseline adoption`、`adopt baseline` 各組合；並掃描 route 模組組出的全部 `transition --to HUMAN_PENDING` 呼叫
  - Then 只有（內環鍵、現態 SCG_VALIDATION、reason 以小寫 `baseline adoption` 起頭）放行；外環鍵一律拒（外環只准前五值）；route 模組從不以其他 reason 組出 `--to HUMAN_PENDING`；`RESEARCH_VERBS` 集合仍恰為 `show`、`transition`、`gate`、`spec-frozen`、`spec-refreeze`
  - 判定：python -m pytest tests/test_research_adopt.py -k AT_961_7_5 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-7-6**（pytest｜`test_research_adopt.py`｜Integration｜AC-R2P-11-7）FSM 子行程環境：白名單重建、內環鍵沿既有行為不強制關閉自動恢復，外環鍵仍固定關閉。
  - Given 假 FSM CLI（記錄收到的環境）；內環鍵與外環鍵各呼叫一次；Bridge 行程環境注入 `BRIDGE_X=1`、`SDD_Y=1`、`PYTHONPATH=x`、`GH_TOKEN=t`
  - When 分別對內環鍵與外環鍵執行 `show`／`transition`
  - Then 兩者環境皆無 `BRIDGE_*`、`PYTHONPATH`、`GH_TOKEN`；外環鍵的呼叫環境含 `SDD_ENABLE_AUTO_RECOVERY=0`（沿 P0）；內環鍵的呼叫環境不含該鍵（ADR-XPLAT-017 D4：「內環鍵沿既有行為」）；子行程經 `popen_platform_kwargs()`、argv 陣列、`shell=False`
  - 判定：python -m pytest tests/test_research_adopt.py -k AT_961_7_6 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-7-7**（pytest｜`test_research_fsm_ops.py`｜Unit｜AC-R2P-14-7）第二個理由前綴 tcs gate（D-97）：只在內環鍵、現態 SCG_VALIDATION 且該鍵已有 Stage-1 凍結時放行 transition --to HUMAN_PENDING，動詞集合不變。
  - Given `sdd_cli.check_research_allowed` 與規則函式（`tcs gate` 前綴屬 PKG-BR-D2，本 AT 的測試新增於既有 `tests/test_research_fsm_ops.py` 末尾，屬 BR-D2 的允許集合，波 2 驗收；BR-D1 的第一波不含本 AT）；內環鍵與外環鍵、現態 SCG_VALIDATION 與其他、已有與沒有 Stage-1 凍結、reason 為 `tcs gate: Stage-2 ready`、`Tcs gate`、`tcs  gate`、`tcs gate`（無冒號）、`baseline adoption: x`
  - When 各組合呼叫檢查函式
  - Then 只有（內環鍵、現態 SCG_VALIDATION、已有 Stage-1 凍結、reason 以小寫 `tcs gate` 起頭）放行；沒有 Stage-1 凍結時以 `tcs gate` 起頭也拒；外環鍵一律拒；`baseline adoption` 前綴的既有行為不變（沿 7-5）；`RESEARCH_VERBS` 恰為既有五個；`decision_trace` 因此記到語意正確的 reason（不是 baseline adoption 的謊言）；`test_sdd_cli.py` 的越界清單與集合釘選零改動仍綠，正負控放在既有 `test_research_fsm_ops.py` 末尾
  - 判定：python -m pytest tests/test_research_fsm_ops.py -k AT_961_7_7 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-7-E-1**（pytest｜`test_research_adopt.py`｜Integration｜AC-R2P-11-7）外環鍵於分流後不被改動：停在 SPEC_FROZEN，狀態檔位元組不變，FSM 呼叫紀錄對外環鍵只有唯讀的 show。
  - Given TMPFSM；外環鍵 `research-demo` 已 SPEC_FROZEN；POST route 完成
  - When 比對分流前後外環鍵狀態檔與呼叫紀錄
  - Then 外環狀態檔位元組不變、現態仍為 SPEC_FROZEN；對外環鍵的呼叫只有 `show`（唯讀）；摘要與凍結記錄留在研究工作區作為出處、不搬遷（PRD FR-R2P-12 邊界條件）
  - 判定：python -m pytest tests/test_research_adopt.py -k AT_961_7_E_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-7-E-2**（pytest｜`test_research_adopt.py`｜Integration｜AC-R2P-11-7）採納序列的計數釘住：恰 1 次 show、5 次 transition、1 次 spec-frozen，且沒有 gate、resume 類動詞。
  - Given 接 7-1 的呼叫記錄
  - When 統計動詞
  - Then show 1、transition 5、spec-frozen 1；`gate`、`spec-refreeze`、`resume-from-escalation` 皆 0；多一次或少一次本 AT 紅
  - 判定：python -m pytest tests/test_research_adopt.py -k AT_961_7_E_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-8-1**（pytest｜`test_research_gitops.py`｜Unit｜AC-R2P-13-4）gitops 允許集合表驅動：每個 P1 允許形態通過驗證，組出的 argv 為陣列且不經 shell。
  - Given `gitops.build_argv(verb, args)` 與 P1 允許表（`status --porcelain`、`rev-parse`、`diff --name-only`、`ls-files`、`worktree list --porcelain`、`-c core.longpaths=true worktree add -b`、`init -b main`、`add -A`〔僅新專案根，軌道 B〕、`add -- <明列路徑…>`〔軌道 A；逐路徑 `check_path` 須在 worktree 內〕、`commit -m`、`remote add origin`、`push -u origin`；gh：`auth status`、`repo create … --private|--public --source . --push`；`tag -a`、`pr create`、`release create` 屬 P2，P1 不入表，⚖P1-10）
  - When 對表內每個形態餵合法參數
  - Then 每個形態回 argv 列表（第一元素為 `git` 或 `gh`）；不含 shell 字元串接；`add -A` 的 cwd 必須在新專案根之內（根外、worktree 內一律拒）；`add --` 帶的每個路徑必須逐一在 worktree 內（`..`、絕對路徑逃逸、符號連結逃逸皆拒）；`-c` 只准 `core.longpaths=true`；`commit -m` 的訊息取自模板常數、不接受呼叫端自由文字；表外任何動詞（含 P2 的 `tag`、`pr`、`release`）於 P1 回 `GitopsDenied`
  - 判定：python -m pytest tests/test_research_gitops.py -k AT_961_8_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-8-2**（pytest｜`test_research_gitops.py`｜Unit｜AC-R2P-13-4）禁止形態逐一被拒：強推、硬重設、clean、stash、檢出路徑、restore 路徑、switch -f、全域與系統層 config。
  - Given `gitops.build_argv` 與子行程啟動計數器（假 `subprocess`）
  - When 逐一嘗試：`push --force`、`push -f`、`push --force-with-lease`、`push --FORCE`、`push --force=x`、`push origin +main`、`push -u origin +main`、`reset --hard`、`reset --merge`、`reset --keep`、`clean -fd`、`stash`、`stash push`、`stash pop`、`checkout -- x`、`checkout -f`、`restore x`、`switch -f`、`switch --discard-changes`、`config --global user.name x`、`config --system x`、`config x y`、`-c core.hooksPath=x status`、`worktree remove`、`branch -D x`
  - Then 每一個皆回 `GitopsDenied`，且子行程啟動計數為 0（在 spawn 之前拒絕）；大小寫與等號變形一律拒絕；拒絕訊息指出被拒的動詞，不洩漏環境；此表與根 `CLAUDE.md` 鐵律五的列舉形態逐項對得上（毀滅形態只擋不放）
  - 判定：python -m pytest tests/test_research_gitops.py -k AT_961_8_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-8-3**（pytest｜`test_research_gitops.py`｜Unit｜AC-R2P-13-4、AC-R2P-11-5）使用者可影響的 argv 片段先過列舉或正規式：選項注入與 shell 元字元一律拒絕。
  - Given `gitops.build_argv` 的使用者片段：分支名、基底 ref、庫名、owner、可見性、路徑
  - When 值取：以 `-` 起頭（`-x`、`--upload-pack=x`）；含 `;`、`|`、`&`、`$(…)`、反引號、換行、空白、NUL；`base_ref` 為 `--orphan`；owner 為 `a/b`、`..`；可見性為 `internal`；路徑含 `..`
  - Then 全部回 `GitopsDenied` 或 `ScaffoldError`；零子行程啟動；合法值（`feature/issue-0007`、`main`、`demo-app`、`octocat`、`PRIVATE`）通過；owner 另需 `^[A-Za-z0-9][A-Za-z0-9-]{0,38}$`
  - 判定：python -m pytest tests/test_research_gitops.py -k AT_961_8_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-8-4**（pytest｜`test_research_gitops.py`｜Integration｜AC-R2P-13-4）子行程形態：argv 陣列、shell 為假、環境白名單重建、經 popen_platform_kwargs，且不寫入使用者家目錄設定。
  - Given 假 `subprocess.Popen` 記錄器；Bridge 行程環境含 `BRIDGE_*`、`SDD_*`、`PYTHONPATH`、`GH_TOKEN`、`HOME`
  - When 經 gitops 執行一個 git 命令與一個 gh 命令
  - Then 每次啟動的 argv 為 list、`shell` 為假、`creationflags` 與 `popen_platform_kwargs()` 一致（Windows 帶 `CREATE_NO_WINDOW`）；git 子行程環境不含 `BRIDGE_*`、`SDD_*`、`PYTHONPATH`、`GH_TOKEN`；gh 子行程環境只多 `GH_TOKEN`（且僅當請求帶 token）；`GIT_AUTHOR_*`、`GIT_COMMITTER_*` 以環境設定；唯讀 git 呼叫（`status`、`rev-parse`、`diff`、`ls-files`、`worktree list`）另帶 `GIT_OPTIONAL_LOCKS=0`；`GIT_CONFIG_GLOBAL` 與 `GIT_CONFIG_SYSTEM` 指向空檔（隔離使用者設定，使測試與使用者機器無關）
  - 判定：python -m pytest tests/test_research_gitops.py -k AT_961_8_4 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-8-5**（pytest｜`test_research_ast_locks.py`｜Contract｜AC-R2P-13-4）能力登記：git 與 gh 子行程只住 gitops；新模組先登記 CAPABILITY 與 EXEC_MODULES，未登記即紅。
  - Given `AgentConsole/engine-bridge/app/` 全樹原始碼；`test_research_capability.py` 的 `CAPABILITY`（新類別 `vcs` 登記 `research/gitops.py`，其餘由 BR-D1 定稿）與 `test_research_ast_locks.py` 的 `EXEC_MODULES`；P1 新模組 `research/route.py`、`research/scaffold.py`、`research/gitops.py`、`research/adopt.py`、`research/scr.py`、`research/decompose_plan.py`、`routers/research_route.py`、`routers/research_scr.py`（PACKAGES §1）
  - When AST 掃描：以字面值 `git`、`gh` 為 argv 首元素的呼叫點與 `subprocess` 使用點；對照登記表；對一個未登記的假新模組跑檢查函式（負控）
  - Then `git`／`gh` argv 首元素字面值只出現在 `research/gitops.py`（既有「研究面不呼叫 git 或 gh」規則改寫為此，§4）；`gitops.py` 為唯一 spawn 該二者的研究模組並列入 `EXEC_MODULES`；`route.py`、`adopt.py`、`scr.py`、`decompose_plan.py` 不直接 spawn（只經 `gitops` 與 `fsm_ops`）；`scaffold.py` 登記為 `rw`（寫檔、無網路、無子行程）；每個新檔皆在 `CAPABILITY` 恰登記一次，實樹與登記表相減為空；未登記的假模組使檢查回報問題（負控）；`research_info` 不由設定模組探測 gh（`gh_cli.authenticated` 維持 `NOT-EVALUABLE`；gh 登入只在預演於 `create_github` 為真時經 gitops 探測）；`app/` 全樹無 `.py` 範本檔（範本檔為 `.tmpl`）
  - 判定：python -m pytest tests/test_research_ast_locks.py -k AT_961_8_5 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-8-6**（pytest｜`test_research_ast_locks.py`｜Contract｜AC-R2P-13-4、AC-R2P-11-7）FSM 單一寫入面不被破壞：新模組不含 tools.fsm_runtime、字面值 spec-frozen 與 spec-refreeze；create_key 呼叫者集合含 :route 路徑。
  - Given `app/` 全樹 AST；既有 AT-960-13-3 的呼叫者鎖（P0 的集合為 `create_project`、`_retry_init`、`_abandon_and_reinit` 三個；§4）
  - When 掃描新模組；列舉 `create_key` 的呼叫鏈終點
  - Then `route.py`、`scr.py`、`decompose_plan.py`、`routers/research_route.py`、`routers/research_scr.py` 不 import `tools.fsm_runtime`、不含字面值 `spec-frozen`、`spec-refreeze`、`underspecified`、`FSM-STATE`（寫檔模組不得提到它）；`create_key` 的呼叫者終點集合為 P0 三處加上 `adopt.adopt_baseline`（PACKAGES §4 第 8 列；本 AT 釘集合大小為 4）；基線採納住新模組 `app/research/adopt.py`（`adopt.adopt_baseline`，D-126）；AST 鎖 C2（`spec_frozen` 與 `approve_baseline` 呼叫只准住 `routers/research.py` 的 HTTP 處理函式）白名單加 `research/adopt.py`，且限內環鍵與 `--stage Stage-1`（呼叫處的 stage 引數必須是字面值 `Stage-1`、鍵參數必須來自內環鍵），紅綠自證夾具各一（`adopt.py` 內以 Stage-1 呼叫＝綠；同檔以 `Gate-0` 或外環鍵呼叫＝紅；其他新模組呼叫＝紅）；`scr.apply_minor` 不呼叫 `fsm_ops.approve_baseline`（D-103）、SCR 的 `HEALING_FAILED` 分支零 `fsm_ops` 寫入呼叫（AC-R2P-19-7）；`creators`（以 `create=True` 呼叫 `run_research_verb` 者）仍只有 `research/fsm_ops.py::create_key`
  - 判定：python -m pytest tests/test_research_ast_locks.py -k AT_961_8_6 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-8-7**（pytest｜`test_research_gitops.py`｜Unit｜AC-R2P-13-4）白名單範圍不變：RESEARCH_VERBS 集合與既有 ALLOWED_VERBS 不變，resume-from-escalation 仍不入。
  - Given `sdd_cli.RESEARCH_VERBS`、`sdd_cli.ALLOWED_VERBS`、既有 `test_sdd_cli.py` 與 `test_research_fsm_ops.py`
  - When 讀集合並跑既有兩檔
  - Then `RESEARCH_VERBS` 恰為 `show`、`transition`、`gate`、`spec-frozen`、`spec-refreeze`；`ALLOWED_VERBS` 恰為既有五個；`resume-from-escalation` 兩表皆無；既有 `test_sdd_cli.py` 零改動全綠（§4 第 18 列）
  - 判定：python -m pytest tests/test_research_gitops.py -k AT_961_8_7 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-8-E-1**（pytest｜`test_research_gitops.py`｜Unit｜AC-R2P-13-4）git 與 gh 的 stderr、stdout 回傳給呼叫端前先脫敏並截尾，且 gitops 不對外洩漏絕對路徑以外的環境資訊。
  - Given 假子行程輸出含 token 樣式、環境變數 dump
  - When 經 gitops 取回輸出
  - Then 輸出內 token 樣式被遮罩；超過 2000 字元者取尾端 2000 字元；環境變數 dump 不入回傳值
  - 判定：python -m pytest tests/test_research_gitops.py -k AT_961_8_E_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-8-E-2**（pytest｜`test_research_gitops.py`｜Unit｜AC-R2P-13-4）push 目的限定：只准 origin 與已驗證的分支，refspec 不得帶強推前綴。
  - Given `gitops.build_argv('push', …)`
  - When 目的為 `origin`、`upstream`、URL、`origin HEAD:refs/heads/x`、`origin +x`
  - Then 只有 `push -u origin <已驗證分支名>` 放行；其餘全拒；零子行程啟動
  - 判定：python -m pytest tests/test_research_gitops.py -k AT_961_8_E_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-9-1**（pytest｜`test_research_tcs_draft.py`｜Integration｜AC-R2P-14-7）tcs-draft 前置：分流 SUCCEEDED、內環鍵 SPEC_FROZEN 且恰有 Stage-1 凍結、已有拆解列（D-110）、無進行中 stage、無 open SCR；任一不成立回 409 並逐條列 unmet。
  - Given `LB`、`RDB`、TMPFSM；專案：未分流；分流失敗；內環鍵 SPEC_FROZEN（Stage-1）但無拆解列；前置齊備；外環 ESCALATION；已有 RUNNING 的 stage；有 OPEN 的 SCR
  - When 各 POST stages/tcs-draft:start
  - Then 前置不成立回 409，`details.unmet[]` 逐條列出（`route_not_succeeded`、`inner_key_not_adopted`、`decomposition_missing`；體例沿 AC-R2P-01-3），reason 為 `fsm_state_conflict`；外環 ESCALATION 409 `escalated`；已有 RUNNING 409 `stage_conflict`；有 OPEN SCR 409 `scr_open`；前置齊備 202；所有 409 零寫入（`research_stage_runs` 列數、內環鍵狀態檔位元組不變）；P0 的 501 骨架已移除（`tcs-draft` 不再回 `not_implemented`；`not_implemented` reason 保留供 P2 骨架，D-111）
  - 判定：python -m pytest tests/test_research_tcs_draft.py -k AT_961_9_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-9-2**（pytest｜`test_research_tcs_draft.py`｜Integration｜AC-R2P-14-7）tcs-draft 的 stage run：DB 記 TCS_DRAFT、編譯為最小授權的 spec-engineer run、prompt-by-reference。
  - Given `LB`、`RDB`；`FC` 研究劇本（含 `(tcs-draft, 0)` 步驟）；框架夾具副本（`spec-engineer-zh.yaml` 與 `TEST-CONTRACT-SPEC-TEMPLATE.md`）
  - When POST tcs-draft:start 並等待 stage 終態；讀 `research_stage_runs`、編譯結果與內環鍵 FSM 呼叫紀錄
  - Then 新增一列 `stage` 為 `TCS_DRAFT`、`status` 先 `QUEUED`／`RUNNING` 後 `SUCCEEDED`；啟動時 Bridge 先對內環鍵 `transition --to SPEC_DRAFTING`（`--reason` 含 `Stage-2` 與研究專案編號）；編譯結果欄（`playbook_sha256`、`config_sha256`、`prompt_manifest`、`allowlist_snapshot`）建立時寫入且之後唯讀；agent 為 `spec-engineer`、輸入為 Bridge 預先寫好的 `03_execution/tcs_inputs.json`（PRD 與 AC 清單）、agent 只寫 `03_execution/tcs_draft.md`；`allowedTools` 不含 Bash、PowerShell、Task、Agent、WebSearch、WebFetch；步驟 prompt 為固定參照句（讀 `.prompts/tcs-draft.md`）、不超過 1000 字元；子行程環境無 `BRIDGE_*`、`SDD_*`、GitHub token；`execution_runs` 零新列
  - 判定：python -m pytest tests/test_research_tcs_draft.py -k AT_961_9_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-9-3**（pytest｜`test_research_tcs_draft.py`｜Integration｜AC-R2P-14-7）TCS 確定性驗證（即 SCG 預檢，D-109）：AT 與凍結 AC 一一對映、AC 全涵蓋、判定指令非空、無機密、檔名合 _freeze 規則，任一不過 stage 失敗且內環鍵留在 SPEC_DRAFTING。
  - Given `LB`、`RDB`；劇本五個變體：缺一個 AC 的 AT；有 AT 無對應 AC（孤兒）；某 AT 判定指令欄為空；內文含假機密樣式（`ghp_FAKE…`）；檔名不合 `_freeze` 的 `_TCS_NAME`；另一合法變體
  - When 各 POST tcs-draft:start 並等待終態
  - Then 五個壞變體 stage `FAILED`、`exit_reason` 為 `tcs_invalid`（細項寫進 `research.run` 事件 payload：缺的 AC 編號、孤兒 AT、欄位名；payload 不含機密原文）；目標 `docs/` 無新檔、不登記 `TCS` 產物、內環鍵現態仍為 SPEC_DRAFTING；再次啟動不重複 `transition --to SPEC_DRAFTING`（先讀現態，已達目標略過）；合法變體通過；驗證規則取自框架 `TEST-CONTRACT-SPEC-TEMPLATE.md` 夾具與 `routers/sdd.py` 的 `_TCS_NAME`（不內嵌第二份）
  - 判定：python -m pytest tests/test_research_tcs_draft.py -k AT_961_9_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-9-4**（pytest｜`test_research_tcs_draft.py`｜Integration｜AC-R2P-14-7）TCS 發佈與登記：通過後發佈到目標 docs/03_testing/contracts，內環鍵依序 transition 到 SCG_VALIDATION 與 HUMAN_PENDING（理由前綴 tcs gate），游標 TCS_PENDING。
  - Given `LB`、`RDB`；劇本三個變體：缺必要章節；有 AC 無 AT；有 AT 無對應 AC
  - When stage 成功後讀工作區、目標 docs、`research_artifacts`、`research_decompositions` 與內環鍵 `show`
  - Then 目標 `docs/03_testing/contracts/TCS-<slug>-<yyyymmdd>.md` 位元組等於 `03_execution/tcs_draft.md`（軌道 A 另以 `add -- <明列路徑>` 與 `commit` 提交）；`research_artifacts` 新增 `kind` 為 `TCS` 的登記（含 sha256）；最近一筆 `research_decompositions` 的 `tcs_rel_path` 與 `tcs_sha256` 為該路徑與雜湊（D-110：拆解列為前置，故必存在）；內環鍵 `decision_trace` 末兩筆為 `SPEC_DRAFTING→SCG_VALIDATION`、`SCG_VALIDATION→HUMAN_PENDING`，後者 `--reason` 以 `tcs gate` 起頭；游標 `flow_phase` 為 `TCS_PENDING`（草擬中為 `TCS_DRAFTING`）；`research.step` 與 `research.run` 事件依序
  - 判定：python -m pytest tests/test_research_tcs_draft.py -k AT_961_9_4 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-9-5**（pytest｜`test_research_tcs_draft.py`｜Integration｜AC-R2P-14-7）TCS 凍結仍走既有 :freeze：帶 TCS 時成功並使內環鍵含 Stage-2，不帶 TCS 時仍 422 missing_tcs；Bridge 不自動凍結。
  - Given TMPFSM 與真 CLI；內環鍵 SPEC_FROZEN（Stage-1）；tcs-draft 成功
  - When 讀 FSM 呼叫紀錄與 `show`；再對既有 `POST /sdd/fsm/{project}:freeze` 以含 TCS 的 `docs[]` 呼叫（走既有端點，不是研究端點）
  - Then Bridge 對內環鍵只做 `transition`（SPEC_DRAFTING、SCG_VALIDATION、HUMAN_PENDING 三次）；沒有 `spec-frozen`、`spec-refreeze`、`gate` 呼叫；`:freeze` 帶 TCS（預設 Stage-2）時成功、內環鍵現態 SPEC_FROZEN 且 `frozen_stages` 含 Stage-2；不帶 TCS 時 422 `missing_tcs`（既有 `test_sdd_freeze.py` 零改動仍綠）；凍結由人在既有介面完成；console-api 於凍結後依衍生規則把游標推回 `BUILD_READY`（D-114 標籤『可開始建置』）
  - 判定：python -m pytest tests/test_research_tcs_draft.py -k AT_961_9_5 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-9-6**（pytest｜`test_research_tcs_draft.py`｜Integration｜AC-R2P-14-7）Stage-2 未凍結時 Bridge 內環鍵現態可被 console-api 讀到且不被 Bridge 自己放行執行（執行閘在 console-api，D-102）。
  - Given `LB`；內環鍵現態 SPEC_DRAFTING、HUMAN_PENDING（TCS 待凍結）與 SPEC_FROZEN 且 Stage-2 已凍結三種；`GET /sdd/fsm/{key}` 的視圖
  - When 讀內環鍵 FSM 視圖的 `frozen_stages` 與 `phase`
  - Then 視圖回傳的 `frozen_stages` 在前兩者不含 Stage-2、第三者含；console-api 執行前置守衛判準唯一取此視圖（見 AT-961-11-6）；Bridge 自身不新增啟動閘、不改 `routers/sdd.py`（`git diff` 為空）
  - 判定：python -m pytest tests/test_research_tcs_draft.py -k AT_961_9_6 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-9-7**（pytest｜`test_research_tcs_draft.py`｜Integration｜AC-R2P-14-7）mock-only 下 tcs-draft 可跑：劇本含 (tcs-draft, 0)，Docker 全棧以 mock claude 走完草擬。
  - Given `app/mock_claude.py` 研究劇本模式；`MOCK_CLAUDE_RESEARCH_SCRIPT` 指向含 `tcs-draft` 步驟的劇本；`mode` 為 `mock-only`
  - When POST tcs-draft:start（以 API 直呼）
  - Then 202 且 stage 成功；劇本缺 `(tcs-draft, 0)` 時非 0 rc 並在 stderr 說明（不靜默成功）；既有劇本鍵 `research`、`draft`、`review-*`、`revise` 的行為與輸出位元組不變（既有 `test_mock_claude_research.py` 零改動全綠）
  - 判定：python -m pytest tests/test_research_tcs_draft.py -k AT_961_9_7 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-9-E-1**（pytest｜`test_research_tcs_draft.py`｜Integration｜AC-R2P-14-7）TCS 草擬不碰已凍結的規格：已發佈 PRD 與 Gate 0 凍結檔位元組不變。
  - Given 接 9-3；PRD 發佈檔與 `01_specs/PRD-v1.0.0.md` 的雜湊
  - When tcs-draft 前後比對
  - Then 兩檔位元組與雜湊不變；`research_prd_versions` 與 `research_gate_decisions` 列數不變；`02_governance/route_decision.json` 位元組不變
  - 判定：python -m pytest tests/test_research_tcs_draft.py -k AT_961_9_E_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-9-E-2**（pytest｜`test_research_tcs_draft.py`｜Integration｜AC-R2P-14-7）tcs-draft 重試與重拆承接：驗證失敗後再啟動走完成功路徑；重拆產生新拆解列時承接前一列的 tcs_rel_path 與 tcs_sha256（D-110）。
  - Given 接 9-3 的失敗狀態；已有拆解列甲（含 `tcs_*`）再重拆得乙列
  - When 排除故障後再 POST tcs-draft:start；POST `:decompose`
  - Then 第二次啟動成功、內環鍵 `decision_trace` 只有一組 `SPEC_DRAFTING` transition（不重複）；乙列的 `tcs_rel_path` 與 `tcs_sha256` 等於甲列（承接）；`research_artifacts(kind=TCS)` 不重複登記相同內容
  - 判定：python -m pytest tests/test_research_tcs_draft.py -k AT_961_9_E_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-10-1**（pytest｜`test_research_decompose.py`｜Integration｜AC-R2P-14-1）觸發拆解（Bridge :decompose，同步 HTTP、非 stage run）：逐 US 呼叫既有拆解服務，covers_ac 由該次呼叫綁定的 AC 清單確定性賦值，產生草稿與 R8 列。
  - Given `LB`、`RDB`；分流已 SUCCEEDED 且 PRD 已凍結的專案（凍結 PRD 含 3 個 US、5 個 AC）；拆解引擎夾具（沿既有 `DecomposeService` 的二段拆解形狀，每次呼叫回放固定樹；夾具模型輸出刻意帶錯誤的 `covers_ac` 以驗證不被採信）
  - When POST `…:decompose` `{requested_by}` 並取回應
  - Then 200 `{decomposition_id, status: DRAFTED, tasks_count, coverage:{total, covered, uncovered[]}}`；`research_decompositions` 新增一列（`path` 為 `C`、`status` 為 `DRAFTED`、`prd_sha256` 等於凍結摘要中 PRD 項、`tasks_count` 等於樹內 task 數、`draft_id` 存第一次呼叫的草稿 id、其餘 id 與完整 JSON 存 `research_artifacts(kind=TASK_DECOMPOSITION)` 內容，D-94）；每個 task 的 `covers_ac` 等於「產生該 task 的呼叫所綁定的 AC 清單」（不採信模型自報，夾具的錯誤值被覆蓋）；`03_execution/task_decomposition.json`（`signed_off` 為假、`prd_sha256`）與 artifacts 登記 sha256 相符（版本遞增）；游標維持 `build`／`ROUTED`（拆解不新增 `flow_phase` 值，D-116：無 V20）；未呼叫任何 FSM 動詞；AutoClaude 與 `app/decompose.py` 零改動（`git diff` 為空）；總耗時寫入證據（中位數超過 120 秒即列症狀，P2 候選＝改 stage run）
  - 判定：python -m pytest tests/test_research_decompose.py -k AT_961_10_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-10-2**（pytest｜`test_research_decompose.py`｜Integration｜AC-R2P-14-1）三道有界閘：超過 24 步、有環、空 prompt 任一不過回 422 結構化錯誤，不截斷、不自動修剪。
  - Given `LB`、`RDB`；拆解引擎夾具的四個變體：恰 24 步；25 步；含環；某節點 prompt 為空
  - When 各觸發拆解
  - Then 24 步通過；25 步、有環、空 prompt 各回 422 `invalid_request`，`violations[].rule` 依序為 `max_steps`、`cycle`、`empty_prompt`（另 `brain_failed`、`brain_unsupported` 沿既有 `gate` 值），並帶 `detail`；失敗時 `research_decompositions` 列 `gate_rejection` 為該閘別（`status` 為 `REJECTED`）、不寫 `task_decomposition.json`、不截斷成 24 步；游標不前進；前置不成立時 409 `fsm_state_conflict`／`stage_conflict`／`scr_open`
  - 判定：python -m pytest tests/test_research_decompose.py -k AT_961_10_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-10-3**（pytest｜`test_research_decompose.py`｜Unit｜AC-R2P-14-2）覆蓋對映：凍結 PRD 的每個 AC 至少被一個 task 的 covers_ac 涵蓋，未覆蓋者逐一列出，未知 AC 編號被拒。
  - Given `decompose.coverage(prd_acs, tasks)` 純函式；PRD AC 集合 `{AC-001..AC-005}`
  - When tasks 的 `covers_ac` 為：全覆蓋；缺 `AC-004`、`AC-005`；多出 `AC-999`（不在 PRD）；同一 AC 被兩個 task 涵蓋；全部為空
  - Then 全覆蓋時 `uncovered` 為空；缺者依字母序列出 `[AC-004, AC-005]`；`AC-999` 回報在 `unknown_ac[]`（草稿仍存但標未決，簽核前須處理，見 AT-961-11-1）；重複涵蓋不影響；全空時 `uncovered` 為五個；PRD AC 集合取自凍結 PRD 的 `#### AC-` 標題機械計數（與 QA 維度 `ac_total` 同判準）
  - 判定：python -m pytest tests/test_research_decompose.py -k AT_961_10_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-10-4**（pytest｜`test_research_decompose.py`｜Integration｜AC-R2P-14-2）簽核前置：未覆蓋者清零或各有人工豁免才可寫入 SIGNED_OFF；豁免理由 1 至 500 字、各自成筆（D-113 單一寫入時點）。
  - Given `LB`、`RDB`；拆解草稿有兩個未覆蓋 AC；Bridge `:decomposition-signoff {decomposition_id, import_record_id, console_project_id, approver, waivers?:[{ac, reason}]}`（IFACE §1.8；console-api 先走既有 import／signoff 取得 `import_record_id`）
  - When POST `:decomposition-signoff`：兩個未覆蓋皆無豁免；一個 AC 缺理由、理由 1 字元、500 字元、501 字元、豁免一個不在未覆蓋集合內的 AC；兩個都豁免或補覆蓋後
  - Then 有未覆蓋且無有效豁免時 422 `invalid_request`（`violations[{field: coverage, rule: uncovered_ac, ac}]`，列出未覆蓋 AC），`status` 不變；理由為空或 501 字元 422；1 與 500 字元通過；豁免不存在或已覆蓋的 AC 422；列非 `DRAFTED`／`SCG_PASSED` 回 409 `fsm_state_conflict`（`details.status`）；`prd_sha256` 不等於現凍結摘要回 409 `decomposition_stale`；兩個都豁免或補覆蓋後同交易寫 `status` 為 `SIGNED_OFF` 與 `import_record_id`（`IMPORTED` 值 P1 不使用，D-113），回 200 `{decomposition_id, status: SIGNED_OFF, artifact_sha256}`；`waivers[]` 每筆含 `ac`、`reason`、`by`、`at`（時間帶時區），隨 `research_artifacts(kind=TASK_DECOMPOSITION)` 新版本（`signed_off`、`signed_off_by`、`signed_off_at`）落地並重寫 `03_execution/task_decomposition.json`，與 DB 列對帳
  - 判定：python -m pytest tests/test_research_decompose.py -k AT_961_10_4 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-10-5**（pytest｜`test_research_decompose.py`｜Integration｜AC-R2P-14-5）stale：PRD 凍結摘要與拆解的 prd_sha256 不符時，拆解標 STALE。
  - Given `LB`、`RDB`；已簽核（`SIGNED_OFF`）的拆解；外環以 SCR 重新凍結使 PRD 摘要改變（以 `research_gate_decisions` 新列模擬）
  - When 呼叫對帳或讀 `GET decomposition` 的衍生旗標；對 `research_decompositions` 做 `status` 更新
  - Then 舊拆解列 `status` 更新為 `STALE`（受控更新守衛允許）；`prd_sha256` 本欄不動（歷史）；`stale` 旗標為真；已簽核拆解列的簽核事實保留（`signed_off_by`、`signed_off_at` 不被抹除）；新拆解需重新拆與簽核（AT-961-11-4 驗執行閘）
  - 判定：python -m pytest tests/test_research_decompose.py -k AT_961_10_5 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-10-6**（pytest｜`test_research_decompose.py`｜Integration｜AC-R2P-14-6）DB 與檔案逐欄相等：task_decomposition.json 的 sha256 與 R8 列相符，簽核版本的正式 goals 與 tasks 數量相等。
  - Given `LB`、`RDB`；拆解已簽核；Console 專案內的 goals 與 tasks 數（由 MiniBridge／既有 import 夾具提供）
  - When 讀檔與 DB；改檔一位元組後呼叫對帳
  - Then 檔案 sha256 等於 `research_artifacts`（kind `TASK_DECOMPOSITION`）登記值；`tasks_count` 等於 JSON 內 task 數且等於已簽核版本落成的正式 tasks 數；改檔後對帳 `task_decomposition` 項為 `drift`（`drift[]` 含 kind、path、expectedSha256、actualSha256）；Bridge 不自動修正任何一邊
  - 判定：python -m pytest tests/test_research_decompose.py -k AT_961_10_6 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-10-7**（pytest｜`test_research_decompose.py`｜Integration｜AC-R2P-14-1）重拆＝新版本：已簽核草稿不可變，只有已簽核的最新版為有效。
  - Given `LB`、`RDB`；甲版已 `SIGNED_OFF`；再觸發拆解（PRD 未變）
  - When 再 POST 拆解；對甲版任一欄做 UPDATE 與 DELETE；查有效版
  - Then 產生新列乙版（`DRAFTED`），甲版列位元組不變（受控守衛擋清單外欄與刪除）；有效版取「已簽核且 `prd_sha256` 等於現凍結摘要的最新版」：乙版簽核前有效版仍為甲版，乙版簽核後為乙版；甲版 `status` 不被改寫為其他值（沒有 SUPERSEDED 列舉；有效性由查詢決定，⚖P1-12）；乙列承接甲列的 `tcs_rel_path` 與 `tcs_sha256`（D-110）；`research_artifacts(kind=TASK_DECOMPOSITION)` 版本遞增而不覆寫舊版
  - 判定：python -m pytest tests/test_research_decompose.py -k AT_961_10_7 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-10-8**（pytest｜`test_research_decompose.py`｜Integration｜AC-R2P-14-1）按 Goal 分批拆解：大型 PRD 單次逾 24 步被拒，改按 Goal 分批後每批不超過 24 步、總數可超過 24。
  - Given `LB`；PRD 含三個 Goal、拆解夾具每個 Goal 20 步（總 60 步）
  - When 先單次整份拆解；再按 Goal 逐批拆解
  - Then 單次整份回 422 `max_steps`（不截斷）；按 Goal 三批各通過且每批 ≤24；合併後 `tasks_count` 為 60、`covers_ac` 對映對合併結果計算；單批超 24 仍被拒
  - 判定：python -m pytest tests/test_research_decompose.py -k AT_961_10_8 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-10-E-1**（pytest｜`test_research_decompose.py`｜Integration｜AC-R2P-14-1）planner 不得繞過人工 signoff：任何拆解路徑都不會產生 signed_off 為真的草稿，也不呼叫 FSM gate 類動詞。
  - Given 拆解流程的全部輸出與 FSM 呼叫紀錄
  - When 跑 10-1 至 10-8 的各路徑並掃描
  - Then 所有 `research_decompositions` 與 JSON 的 `signed_off` 皆為假（簽核只由 console-api 經既有 signoff 路徑造成）；FSM 呼叫紀錄無 `gate`、`spec-frozen`；Bridge 內無任何寫入 `signed_off` 為真的程式路徑（AST：字面值 `signed_off` 為真的賦值為 0 處）
  - 判定：python -m pytest tests/test_research_decompose.py -k AT_961_10_E_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-12-1**（pytest｜`test_research_scr.py`｜Integration｜AC-R2P-19-1）發起 MINOR SCR：寫 research_scr 列、停止進行中 run、新的執行回 409 scr_open、凍結 PRD 位元組不變、游標進 SCR_OPEN。
  - Given `LB`、`RDB`、TMPFSM；分流完成、內環鍵 IMPLEMENTATION；外環鍵 SPEC_FROZEN；凍結 PRD 雜湊（進行中 run 的停止由 console-api 先呼既有 stop 用例，D-103，不在 Bridge 本 AT）
  - When POST `:scr` `{kind: MINOR, source_kind: HUMAN, reason, reason_class: AC_VAGUE, affected_sections: ["5.2"], requested_by}`
  - Then 202 `{scr_no: 1, status: OPEN}`；處理序固定：驗輸入→現態矩陣預檢（不合 409 `fsm_state_conflict`，零列零 FSM 寫入）→`scr_limit` 檢查→寫 `research_scr` 一列→外環鍵 `transition --to SPEC_DRAFTING`（`--reason` 含 `進入 Stage Gate-0-SCR1`）；`research_scr` 恰一列：`status` 為 `OPEN`、`requested_by`、`requested_at`（帶時區）、`affected_sections`、`reason`、`reason_class` 皆為所給；內環鍵現態仍為 IMPLEMENTATION（AC-R2P-19-1 的「內環鍵回 IMPLEMENTATION」依 D-115 勘誤為「進行中 run 被停止；內環鍵現態不變」）；凍結 PRD 檔與 `frozen_digests` 位元組不變；游標 `flow_step` 為 `studio`、`flow_phase` 為 `SCR_OPEN`；事件 `research.scr`（`{scrNo, kind, status}`）與 `research.step` 各一筆
  - 判定：python -m pytest tests/test_research_scr.py -k AT_961_12_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-12-2**（pytest｜`test_research_scr.py`｜Unit｜AC-R2P-19-5）SCR 輸入閘：理由、分類、受影響章節三類違規各自成筆，零 research_scr 列、零 FSM 呼叫、游標不變。
  - Given `scr.validate_request(body, frozen_prd)` 與整合層 `LB`；凍結 PRD 的章節與 AC 清單
  - When 送：理由空、501 字元；`reason_class` 為 `BUG`；`affected_sections` 含不存在章節、不存在 AC；三種違規同時；`kind` 為 `MEDIUM`；`source_kind` 為 `OTHER`；1 與 500 字元理由與合法分類
  - Then 422 `invalid_request`，`violations[]` 每個違規一筆（規則 `reason_empty`、`reason_too_long`、`reason_class_invalid`、`affected_unknown`；三違規同時為三筆）；`kind` 與 `source_kind` 值域違規在 console-api 為 400、在 Bridge 為 422；1 與 500 字元通過；任何違規情境前後 `research_scr` 列數、FSM 呼叫紀錄（0 筆）、游標、`scr_open` 狀態皆不變
  - 判定：python -m pytest tests/test_research_scr.py -k AT_961_12_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-12-3**（pytest｜`test_research_scr.py`｜Integration｜AC-R2P-19-3）SCR 開啟而新 Gate 0 尚未完成時，恢復舊 run 回 409 scr_open，內環唯讀。
  - Given 接 12-1 的專案；內環鍵狀態檔位元組
  - When 呼叫 Bridge 側的內環啟動守門函式 `scr.guard_inner_start(research_id)`（console-api 啟動入口的 409 另由 AT-961-11-5 驗；守門函式名以 PACKAGES 定稿為準），分別以「恢復舊 run」與「啟動新 run」兩種意圖
  - Then 409 `scr_open`；內環鍵狀態檔位元組不變、FSM 呼叫紀錄零寫入；`research_scr` 狀態仍為 `OPEN`
  - 判定：python -m pytest tests/test_research_scr.py -k AT_961_12_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-12-4**（pytest｜`test_research_scr.py`｜Integration｜AC-R2P-19-6）MINOR 上限（D-104 保守計）：同一研究專案內 kind 為 MINOR 且 status 為 OPEN、APPROVED 或 APPLIED 的列已有 2 筆，第 3 次回 409 scr_limit 並要求改 MAJOR。
  - Given `LB`、`RDB`；同一專案已有兩筆 MINOR：一筆 `APPLIED`、一筆 `APPROVED`；另一專案有 2 筆 MINOR 其一為 `REJECTED`、一筆 `SUPERSEDED`（MAJOR 取代者）、一筆 `OPEN`
  - When 第 3 次 POST `:scr` MINOR；再 POST MAJOR；另一專案 POST MINOR；把第一專案一筆 MINOR 改 `REJECTED` 後再 POST MINOR
  - Then 第 3 次 409 `scr_limit`（`details.limit` 為 2、`details.used` 為 2、`details.hint` 為改 MAJOR）、零新列；MAJOR 通過（不受限）；另一專案只計 `OPEN`、`APPROVED`、`APPLIED`（`REJECTED` 與 `SUPERSEDED` 不佔額度）故其第 3 次依實際有效列數判定；把一筆改為 `REJECTED` 後第一專案再 POST MINOR 通過；上限常數 `SCR_MINOR_MAX` 為 2（PRD 勘誤：「同一 Stage」→「同一研究專案」，永不超過 FSM `SPEC_AUDIT_MAX_PER_STAGE`；⚖P1-14 已依 D-104 定案）
  - 判定：python -m pytest tests/test_research_scr.py -k AT_961_12_4 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-12-5**（pytest｜`test_research_scr.py`｜Integration｜AC-R2P-19-4）MAJOR SCR：建立新研究專案（parent、slug、新外環鍵），舊專案游標不變，舊內環鍵不動。
  - Given `LB`、`RDB`、TMPFSM；舊專案 `research-demo`（slug `demo`，`rp_no` 為 7）與其內環鍵（狀態檔位元組已記）
  - When POST `:scr` `{kind: MAJOR, source_kind: HUMAN, reason, reason_class: EVIDENCE, affected_sections: []}`
  - Then 新 `research_projects` 列：`parent_research_id` 為舊專案、slug 為 `demo-scr1`、外環鍵 `research-demo-scr1` 位於 AGENT_LOAD（經 `show` 建檔，環境固定關閉自動恢復）、新 `rp_no`、游標 topic／INGESTED；舊專案 `research_scr` 列 `successor_research_id` 為新專案（受控清單內欄位）、`status` 為 `SUPERSEDED`；舊專案游標的 `flow_step` 與 `flow_phase` 不變、`flow_detail` 為「已被 RP-NNNN 取代」（NNNN 為新專案編號）；舊內環鍵狀態檔位元組不變、FSM 呼叫紀錄對舊內環鍵 0 筆寫入、不呼叫 `TERMINATED`；回應含新 `researchId`
  - 判定：python -m pytest tests/test_research_scr.py -k AT_961_12_5 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-12-6**（pytest｜`test_research_scr.py`｜Integration｜AC-R2P-19-7）來源類別 HEALING_FAILED：只產生 resume-from-escalation 指令與 research_scr 記錄，不呼叫任何 FSM 寫入動詞。
  - Given `LB`、`RDB`、TMPFSM；內環鍵現態 ESCALATION；FSM 呼叫紀錄
  - When POST `:scr` `{kind: MINOR, source_kind: HEALING_FAILED, …}`
  - Then 200 回 `recovery`（`target`＝`SPEC_DRAFTING`、`powershell`、`posix` 三個字串，後兩者含 `resume-from-escalation --to SPEC_DRAFTING` 與內環鍵與狀態目錄的絕對路徑，可複製）；`research_scr` 一列（`source_kind` 為 `HEALING_FAILED`、`status` 為 `OPEN`）；FSM 呼叫紀錄對任何鍵的寫入動詞為 0 筆（`show` 唯讀可）；`resume-from-escalation` 不在 `RESEARCH_VERBS` 與 `ALLOWED_VERBS`（沿 AT-961-8-7）；Bridge 不 `:stop` 任何 run（無進行中 run）
  - 判定：python -m pytest tests/test_research_scr.py -k AT_961_12_6 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-12-7**（pytest｜`test_research_scr.py`｜Integration｜AC-R2P-19-1、AC-R2P-19-3）同一專案同時只有一筆 OPEN 的 SCR：已有 OPEN 時再發起回 409 scr_open。
  - Given 接 12-1；`research_scr` 有一列 `OPEN`
  - When 再 POST `:scr`（MINOR、MAJOR 各一次）
  - Then 皆 409 `scr_open`、零新列、零 FSM 呼叫、零 `:stop`；`OPEN` 列轉 `APPLIED` 後可再發起
  - 判定：python -m pytest tests/test_research_scr.py -k AT_961_12_7 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-12-E-1**（pytest｜`test_research_scr.py`｜Integration｜AC-R2P-19-1）發起 SCR 時沒有進行中 run 不是錯誤：:stop 為冪等，SCR 仍成立。
  - Given 內環無進行中 run
  - When POST `:scr`
  - Then 202；不呼叫 `:stop`（或呼叫回 404 被視為已停）；`research_scr` 一列；沒有 5xx
  - 判定：python -m pytest tests/test_research_scr.py -k AT_961_12_E_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-12-E-2**（pytest｜`test_research_scr.py`｜Integration｜AC-R2P-19-1）發起 MINOR SCR 時外環轉態失敗的補償（SCG-4 一審 F-09；RELEASE_READY 勘誤批次新增）：SCR 列標 REJECTED、游標還原、錯誤原樣拋出、槽位釋出可再開。
  - Given `LB`、`RDB`；內環鍵在 IMPLEMENTATION；外環 FSM 的 `transition` 被注入失敗（回 502）
  - When POST `:scr`（MINOR）；還原真實轉態後再 POST `:scr` 一次
  - Then 第一次回 502（錯誤原樣）；`research_scr` 恰一列且 `status` 為 `REJECTED`（不留永遠 OPEN 的列）；游標等於發起前（`flow_step`、`flow_phase`、`flow_status` 不變）；第二次回 202（`REJECTED` 釋出槽位）
  - 判定：python -m pytest tests/test_research_scr.py -k AT_961_12_E_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-13-1**（pytest｜`test_research_scr_fsm.py`｜Integration｜AC-R2P-19-8、AC-R2P-19-2）MINOR 收尾序列於暫存狀態目錄實跑：外環重走、Gate-0-SCR 核准、內環五步，decision_trace 等於人工等價序列。
  - Given `SDD_ROOT`（真 CLI；缺則 TOOL-ABSENCE，SCG-4 須 0 skipped）、TMPFSM；外環鍵 SPEC_FROZEN、內環鍵 IMPLEMENTATION（Stage-1 與 Stage-2 已凍結）；SCR（MINOR）已 `OPEN`（外環鍵已 `transition → SPEC_DRAFTING`，見 12-1）；一份「人工等價序列」夾具（ADR-XPLAT-017 附錄 A 的指令序列，以同一 CLI 手跑於另一份暫存狀態目錄）
  - When 外環以夾具劇本走起草、審查 PASS、gate；ADMIN POST `:approve-baseline`（偵測到 OPEN 的 MINOR SCR：Stage 為 `Gate-0-SCR1`）；同一請求內由 `scr.apply_minor()` 對內環鍵依序 `transition --to SPEC_AUDIT`、發佈新 PRD 到目標 `docs/`（複製與 sha256）、`spec-refreeze`、`transition --to PR_REVIEW`、`gate PR_REVIEW FAIL`
  - Then 各步 rc 為 0；`:approve-baseline` 回 200 並含 `scr_apply:{status: APPLIED}`；內環終態 IMPLEMENTATION（`gate PR_REVIEW FAIL` 回傳 `next_state` 為 IMPLEMENTATION）；`research_scr.impl_fsm_actions` 逐筆記錄實際呼叫序列（動詞、參數摘要、結果、時間，含發佈步驟），其動詞序為 `transition(SPEC_AUDIT)`、`publish`、`spec-refreeze`、`transition(PR_REVIEW)`、`gate(PR_REVIEW,FAIL)`；內環與外環兩份 `decision_trace` 與人工等價序列夾具的 `decision_trace` 相同（逐筆比對 from、to、trigger；時間戳與 reason 內的 id 先正規化）；`apply_minor` 不呼叫 `fsm_ops.approve_baseline`（AST，沿 AT-961-8-6）；證據（`show` 前後全文）逐字貼入整合證據檔（PRD §8.1 P1 出口 (g)）
  - 判定：python -m pytest tests/test_research_scr_fsm.py -k AT_961_13_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-13-2**（pytest｜`test_research_scr_fsm.py`｜Integration｜AC-R2P-19-8）內環現態矩陣：IMPLEMENTATION、EXECUTION_EVALUATION、ADVERSARIAL_EVALUATION、PR_REVIEW 直接起跑，SPEC_AUDIT 現態略過第一個 transition。
  - Given TMPFSM 與真 CLI（或 `fake_sdd` 以邊表鏡像，含對拍鎖）；內環鍵分別置於五個現態；Gate-0-SCR 已核准
  - When 各執行內環收尾序列
  - Then 前四者呼叫序為 `transition SPEC_AUDIT`、`spec-refreeze`、`transition PR_REVIEW`、`gate PR_REVIEW FAIL`（含發佈步驟）；SPEC_AUDIT 現態略過第一個 transition（呼叫紀錄無 `transition --to SPEC_AUDIT`）；PR_REVIEW 現態仍先 `transition SPEC_AUDIT`（`PR_REVIEW→SPEC_AUDIT` 是合法邊）；現態矩陣表驅動，來源為 `transition_rules` 邊表的 Bridge 內鏡像（與 P0 `_HAPPY_PATH` 鏡像同一份對拍測試），無第二套狀態機
  - 判定：python -m pytest tests/test_research_scr_fsm.py -k AT_961_13_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-13-3**（pytest｜`test_research_scr_fsm.py`｜Integration｜AC-R2P-19-8）RTM_VERIFY 與 RELEASE_READY 現態：先 gate FAIL 退回 IMPLEMENTATION 再起跑，回傳不是 IMPLEMENTATION 即回報 BLOCKED 不重試。
  - Given TMPFSM 與真 CLI；內環鍵分別在 RTM_VERIFY、RELEASE_READY；另一組使 `gate` 回傳 `next_state` 為 ESCALATION（以預耗盡的重試計數構造）
  - When 各執行序列
  - Then RTM_VERIFY：先 `gate RTM_VERIFY FAIL`、RELEASE_READY：先 `gate RELEASE_READY FAIL`（`--reason` 必填、非空）；回傳 IMPLEMENTATION 則續跑；回傳 ESCALATION 或其他則序列停止、`research_scr.impl_fsm_actions` 記到 `gate` 為止、回報 `BLOCKED`（`flow_detail` 為 `scr_blocked:<next_state>`，⚖P1-6）、不重試、不續呼叫任何後續動詞
  - 判定：python -m pytest tests/test_research_scr_fsm.py -k AT_961_13_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-13-4**（pytest｜`test_research_scr_fsm.py`｜Integration｜AC-R2P-19-8）現態不在矩陣內（含任何 ESCALATION*）回 409 fsm_state_conflict，零 FSM 寫入、不起跑。
  - Given TMPFSM；內環鍵分別在 INIT、AGENT_LOAD、SPEC_DRAFTING、SPEC_FROZEN、ESCALATION、ESCALATION_FINAL、AUTO_RECOVERY_ATTEMPT、RELEASE
  - When 對每個現態執行序列
  - Then 皆 409 `fsm_state_conflict`（`details.current_state`）；FSM 呼叫紀錄零寫入（`show` 唯讀可）；`impl_fsm_actions` 維持空陣列；目標 `docs/` 無新檔（發佈步驟未執行）
  - 判定：python -m pytest tests/test_research_scr_fsm.py -k AT_961_13_4 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-13-5**（pytest｜`test_research_scr_fsm.py`｜Integration｜AC-R2P-19-8）gate PR_REVIEW FAIL 被判同模式而改走 SPEC_AUDIT 時回報 BLOCKED，不重試。
  - Given TMPFSM 與真 CLI；以相同 `--reason` 預先累積兩次 `PR_REVIEW` FAIL 使第三次被判同模式
  - When 執行序列
  - Then `gate` 回傳 `next_state` 為 SPEC_AUDIT（≠IMPLEMENTATION）；Bridge 回報 `BLOCKED`、`impl_fsm_actions` 記錄該 `gate` 與回傳值、後續不呼叫任何動詞、`gate` 只呼叫一次（不重試）；SCR 狀態保持 `OPEN` 並於 `flow_detail` 說明（沿 13-3 格式）
  - 判定：python -m pytest tests/test_research_scr_fsm.py -k AT_961_13_5 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-13-6**（pytest｜`test_research_scr_fsm.py`｜Integration｜AC-R2P-19-2）新版本與舊凍結版：Gate-0-SCR 核准後版本遞增、新增 R6 列，舊凍結版保留可比對，SCR 轉 APPLIED，既有拆解標 STALE。
  - Given 接 13-1 的 Gate-0-SCR 核准時點；舊 `PRD-v1.0.0.md`、舊 Gate 0 決定列、已簽核拆解
  - When 讀 DB 與檔案；ADMIN 於核准時帶 `versionBump` 為 `MAJOR`（版本為 `v2.0.0`）、不帶（`v1.<n>.0`）各一次（契約 API-RP-12 補此選填欄，僅 SCR 核准時有效，RISKS (b)-8、D-115）
  - Then 新 PRD 為 `v1.<n>.0`（n 為 SCR 序號；`versionBump` 為 `MAJOR` 時為 `v2.0.0`）；`research_gate_decisions` 新增一列（`stage` 為 `Gate-0-SCR<n>`、新 `frozen_digests`）、舊列位元組不變；舊 `PRD-v1.0.0.md` 位元組不變、新檔 `PRD-v1.<n>.0.md` 並存；`research_scr.status` 為 `APPLIED`、`prd_from_version_no` 與 `prd_to_version_no` 皆有值；既有拆解標 `STALE`；`versionBump` 在無 OPEN SCR 的一般核准時被拒（422 `invalid_request`）
  - 判定：python -m pytest tests/test_research_scr_fsm.py -k AT_961_13_6 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-13-7**（pytest｜`test_research_scr_fsm.py`｜Integration｜AC-R2P-19-4）游標：SCR(MINOR) 發起後在 studio／SCR_OPEN，新 Gate 0 完成並發佈後回 build（Target Scope 變更才回 route）。
  - Given `LB`、`RDB`；SCR 全程（發起、重走、核准、內環收尾）；兩組：Target Scope 不變、變更
  - When 逐階段讀游標（`flow_step`、`flow_phase`）與 `research.step` 事件
  - Then 發起後 `studio`／`SCR_OPEN`；重走起草與審查期間 `flow_phase` 隨之變化但 `flow_step` 維持 `studio`；核准並發佈後：Target Scope 不變回 `build`、變更回 `route`；每次游標變更皆附一筆 `research.step` 事件（W-R1）；`SCR_OPEN` 期間對帳的 `fsm_flow_mapping` 不報 drift（見 AT-961-20-3）
  - 判定：python -m pytest tests/test_research_scr_fsm.py -k AT_961_13_7 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-13-8**（pytest｜`test_research_scr_fsm.py`｜Integration｜AC-R2P-19-8）發佈順序與失敗：SPEC_AUDIT 之後才發佈；發佈失敗中止序列並記錄到失敗處。
  - Given TMPFSM；檔案寫入鉤子記錄「何時寫入目標 docs」相對於 FSM 呼叫的順序；注入發佈故障（目的檔唯讀）
  - When 執行序列兩次（正常、故障）
  - Then 正常時寫檔事件的順序位於 `transition SPEC_AUDIT` 之後、`spec-refreeze` 之前（序列號比較）；故障時 `impl_fsm_actions` 含 `transition(SPEC_AUDIT)` 與失敗的 `publish`（rc 非 0 與原因）、無 `spec-refreeze` 與其後；目標 docs 無半寫檔；回報 `BLOCKED`（沿 13-3 格式）
  - 判定：python -m pytest tests/test_research_scr_fsm.py -k AT_961_13_8 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-13-9**（pytest｜`test_research_scr_fsm.py`｜Integration｜AC-R2P-19-8）spec-refreeze 的參數與子行程環境：--doc 為目標 docs 相對路徑、--root 為目標根、--approver 為 JWT subject。
  - Given 假 FSM CLI（記錄 argv 與環境）；SCR 序列
  - When 執行序列
  - Then `spec-refreeze` 的 argv 含 `--doc <目標 docs/ 相對 POSIX 路徑>`（至少一個）、`--root <目標根>`、`--reason`（含 `SCR-<k>`、PRD 版本 a→b 與 `gate_decision` id）、`--approver <JWT subject>`；外環鍵呼叫環境含 `SDD_ENABLE_AUTO_RECOVERY=0`、內環鍵不含；環境無 `BRIDGE_*`
  - 判定：python -m pytest tests/test_research_scr_fsm.py -k AT_961_13_9 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-13-E-1**（pytest｜`test_research_scr_fsm.py`｜Integration｜AC-R2P-19-2）預算重新計：SCR 重走起草後，Gate-0-SCR 核准時四個閘的計數一併歸零。
  - Given TMPFSM 與真 CLI；外環鍵在 SCR 前 `SCG_VALIDATION.current_count` 為 1
  - When 走完 SCR 的 Gate-0-SCR 核准後讀 `show` 的 `retry_gates`
  - Then 四個閘 `current_count` 皆為 0（`spec-frozen` 對四閘歸零，ADR-XPLAT-017 D5）；SCR 期間的審查預算為全新 3 次（以再三次 `gate FAIL` 驗證第 3 次進 ESCALATION）
  - 判定：python -m pytest tests/test_research_scr_fsm.py -k AT_961_13_E_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-13-E-2**（pytest｜`test_research_scr_fsm.py`｜Integration｜AC-R2P-19-8）序列中任一步 FSM 非 0 結束即停止：後續不執行，impl_fsm_actions 含失敗步驟。
  - Given 假 FSM CLI 在第 k 次呼叫回非 0（k 依序取 1 至 5 的每個位置）
  - When 各執行序列
  - Then 每個 k：第 k 步之後零呼叫；`impl_fsm_actions` 長度為 k 且末筆 rc 非 0；回報 `BLOCKED`；不重試；目標 docs 的發佈檔狀態與失敗點一致
  - 判定：python -m pytest tests/test_research_scr_fsm.py -k AT_961_13_E_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-13-E-3**（pytest｜`test_research_scr_fsm.py`｜Integration｜AC-R2P-19-8）核准即套用失敗不留空窗：apply_minor 失敗時 SCR 停在 APPROVED，回應帶 scr_apply 狀態，ADMIN 以 :scr-apply 重試，重試冪等。
  - Given TMPFSM；Gate-0-SCR 核准成功；內環序列於第三步（`spec-refreeze`）注入 FSM 非 0；排除故障
  - When 讀 `:approve-baseline` 回應；POST `:scr-apply`（ADMIN）兩次；以 OPERATOR 權杖呼叫 `:scr-apply`
  - Then 核准回 200 且 `scr_apply:{status: FAILED, detail}`、`research_scr.status` 為 `APPROVED`、外環已 `SPEC_FROZEN`（Gate 0 決定列已寫）；Bridge `:scr-apply {scr_no, approver}` 重試依 `impl_fsm_actions` 與內環現態續做（不重做已成功的 `transition(SPEC_AUDIT)` 與發佈）、成功後 `APPLIED`、游標回 `build`、拆解標 `STALE`；`BLOCKED` 回 200 `{status: BLOCKED, detail}` 且 SCR 維持 `APPROVED`；SCR 非 `APPROVED` 或內環現態不在矩陣 409 `fsm_state_conflict`；第二次重試冪等（零 FSM 寫入、回 200）；console-api `POST …/scr/{scrNo}/apply` 僅 ADMIN（OPERATOR 403 `ACCESS_DENIED`，Bridge 請求數 0；AT-961-15-6 驗矩陣）
  - 判定：python -m pytest tests/test_research_scr_fsm.py -k AT_961_13_E_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-16-1**（pytest｜`test_research_capabilities_p1.py`｜Integration｜AC-R2P-04-11、AC-R2P-13-7）capabilities 十三鍵不變、值取真：scaffold_root、scaffold_templates、repo_writable 在 P1 取實值；gh_cli.authenticated 維持 NOT-EVALUABLE（D-98）。
  - Given `LB` 於本機模式：`BRIDGE_SCAFFOLD_ROOT` 已設且可寫（D-96：無預設）、`BRIDGE_REPO_ROOT` 指向暫存 repo（覆寫，未設＝現行 `REPO_ROOT`）、PATH 有 git 與 gh（假 gh）；範本目錄含 `python-fastapi`
  - When GET `/research/capabilities`；改 `BRIDGE_SCAFFOLD_ROOT` 為未設再 GET；改 `BRIDGE_REPO_ROOT` 為唯讀目錄再 GET
  - Then `scaffold_root` 為設定的絕對路徑（未設為 null）；`scaffold_templates` 為目錄掃描結果（含 `python-fastapi`）；`repo_writable` 讀 `BRIDGE_REPO_ROOT`（唯讀時為假）；`gh_cli` 為 `{ok, authenticated: "NOT-EVALUABLE"}`（不起子行程）；`git` 為 `{ok, version: "NOT-EVALUABLE"}`；回應仍恰 13 鍵（`INFO_KEYS` 與 `CAPABILITY_EXTRA_KEYS` 不變）；本檔稱「五鍵」＝本 AT 與 AT-961-16-5 涵蓋的 `scaffold_root`、`scaffold_templates`、`repo_writable`、`gh_cli`、`git` 五個與分流停用有關的鍵
  - 判定：python -m pytest tests/test_research_capabilities_p1.py -k AT_961_16_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-16-2**（pytest｜`test_research_capabilities_p1.py`｜Integration｜AC-R2P-04-11）/health/deep 的 research 物件鍵集合維持八個，mode 判定不變，P1 值語意更新。
  - Given `LB`：找得到 claude 與 git；找不到 claude；既有 `test_health_deep.py` 與 `test_research_settings.py`
  - When GET `/health/deep`
  - Then `research` 物件恰八鍵（`mode`、`root`、`db`、`claude_cli`、`gh_cli`、`git`、`web_layer_enabled`、`scaffold_templates`）；找得到 claude 與 git 為 `local`、找不到 claude 為 `mock-only`；`scaffold_templates` 與 `gh_cli` 的值同 16-1；`/health/deep` 的狀態碼與無研究設定時相同（不影響 503 判定）；既有兩檔中釘 P0 停用值的斷言依 §4 第 8、9 列只改預期值
  - 判定：python -m pytest tests/test_research_capabilities_p1.py -k AT_961_16_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-16-3**（pytest｜`test_research_capabilities_p1.py`｜Integration｜AC-R2P-11-6、AC-R2P-04-11）容器模式：無 gh、repo 唯讀、未設 scaffold 根時 capabilities 如實回報，預演回缺項。
  - Given `LB` 模擬容器環境（PATH 無 gh、repo 不可寫、`BRIDGE_SCAFFOLD_ROOT` 未設）
  - When GET capabilities；POST route-preview 軌道 A、軌道 B
  - Then `gh_cli.ok` 為假、`repo_writable` 為假、`scaffold_root` 為 null、`scaffold_templates` 為 `[]`（未設 scaffold 根時不列）；預演回 422 `route_unsupported_in_deployment`（沿 AT-961-3-5）；伺服器端不因 UI 停用而放行（API 直呼仍驗）
  - 判定：python -m pytest tests/test_research_capabilities_p1.py -k AT_961_16_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-16-E-1**（pytest｜`test_research_capabilities_p1.py`｜Unit｜AC-R2P-13-7）scaffold_templates 的目錄掃描規則：只認合法名稱、含必要檔的目錄；非法或空目錄不列。
  - Given 夾具範本樹：`python-fastapi`（完整）、`Bad Name`（非法名）、`empty`（空目錄）、`node`（含必要檔）
  - When 掃描
  - Then 清單依字母序為 `["node", "python-fastapi"]`；`Bad Name` 與 `empty` 不列；新增合法目錄即出現、刪除即消失（證明取自目錄）
  - 判定：python -m pytest tests/test_research_capabilities_p1.py -k AT_961_16_E_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-20-1**（pytest｜`test_research_reconcile.py`｜Integration｜AC-R2P-23-1）route_decision 項：DB 路由決定列與 route_decision.json 的 sha256 對帳，漂移與缺席各判 drift，兩側皆缺席維持 ok 且 present 為假。
  - Given `LB`、`RDB`；專案甲無分流；乙分流 SUCCEEDED 且 `02_governance/route_decision.json` 在、其 sha256 與 `research_artifacts(kind=ROUTE_DECISION)` 最新版登記相符；丙改檔一位元組；丁 DB 有列而檔案缺席
  - When POST reconcile 四次
  - Then 甲：`route_decision` 為 `ok`、`present: false`；乙：`ok`、`present: true`；丙、丁：`drift`，`drift[]` 含 kind、path、expectedSha256（DB／登記值）、actualSha256（檔案；缺席為 null）；`consistent` 僅在全部 `ok` 時為真；每次呼叫追加一筆 `research.reconcile` 事件；呼叫前後檔案位元組與 DB 列（事件除外）不變
  - 判定：python -m pytest tests/test_research_reconcile.py -k AT_961_20_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-20-2**（pytest｜`test_research_reconcile.py`｜Integration｜AC-R2P-23-1）task_decomposition 項：DB R8 與 task_decomposition.json 對帳，改檔與缺席判 drift。
  - Given 同 20-1 的四種專案，改為拆解（`03_execution/task_decomposition.json` 與 `research_artifacts(kind=TASK_DECOMPOSITION)` 最新版；D-116：R8 JSON 與 waivers 以 artifacts 承載並以 sha256 對帳）
  - When POST reconcile 四次
  - Then 判定規則同 20-1（`task_decomposition` 項）；兩側皆缺席為 `ok` 且 `present: false`；`STALE` 的拆解仍以其登記雜湊對帳（stale 不是 drift）；六項檢查名與順序不變（`fsm_flow_mapping`、`prd_sha256`、`review_card`、`evidence_matrix`、`task_decomposition`、`route_decision`）
  - 判定：python -m pytest tests/test_research_reconcile.py -k AT_961_20_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-20-3**（pytest｜`test_research_reconcile.py`｜Unit｜AC-R2P-23-1）fsm_flow_mapping 對映表增列 P1 DB 游標組合（D-121）：只用 DB 游標值，衍生相態不入對映，TCS_PENDING 加 Stage-2 已凍結列為待校正而非 drift。
  - Given 純函式 `flow_fsm_mapping_ok(fsm_state, flow_step, flow_phase, stage2_frozen)` 與 PRD §5.1.1 對映表；對帳看外環鍵，內環的 Stage-2 凍結旗標由內環 FSM 視圖提供
  - When 逐列：外環 SPEC_FROZEN 配 route／FROZEN、route／ROUTING、build／ROUTED、build／TCS_DRAFTING、build／TCS_PENDING（內環 Stage-2 未凍結）（合法）；外環 SPEC_FROZEN 配 build／TCS_PENDING 且 Stage-2 已凍結（待校正，非 drift）；外環 SPEC_FROZEN 配 studio、topic（不合法）；外環 SPEC_FROZEN 配 build／BUILD_READY、build／PAUSED（衍生相態不是 DB 游標值，視為不合法輸入並回報，不得出現在對映表）；SCR 期間外環 SPEC_DRAFTING、SCG_VALIDATION、HUMAN_PENDING 配 studio／SCR_OPEN（合法）；外環 SPEC_FROZEN 配 studio／SCR_OPEN（SCR 剛發起尚未 transition，合法）；外環 ESCALATION 配 route（不合法）；外環 SPEC_DRAFTING 配 route（不合法）
  - Then 合法列回真、不合法列回假並附雙方值、待校正列回第三態 `pending_correction`（不計為 drift、`consistent` 不因它為假；校正見 AT-961-25-2）；P0 既有各列結果不變（既有 `AT-960-21-2` 零改動仍綠）；所有判定由表驅動、對映表只含 DB 游標值（`BUILD_READY`、`PAUSED` 不入表；D-121）；不新增第二套狀態機
  - 判定：python -m pytest tests/test_research_reconcile.py -k AT_961_20_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-20-4**（pytest｜`test_research_reconcile.py`｜Integration｜AC-R2P-23-4）分流時點自動對帳：route 成功路徑內恰一筆對帳事件、consistent 為真，失敗路徑不產生。
  - Given `LB`、`RDB`；兩個專案：分流成功；分流失敗（`GIT_SWITCH` 故障）
  - When 讀 `research_events` 的 `research.reconcile`
  - Then 成功：route 流程內自動執行恰一次對帳，payload 的 `consistent` 為真、`driftCount` 為 0，事件序號接續；失敗：該流程不產生對帳事件（路由列未 `SUCCEEDED` 前不到對帳時點）；Gate 0 時點的對帳事件仍恰一筆（P0 行為不變）；結果可於交付頁檢視屬 P2（不在本 AT）
  - 判定：python -m pytest tests/test_research_reconcile.py -k AT_961_20_4 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-20-E-1**（pytest｜`test_research_reconcile.py`｜Integration｜AC-R2P-23-1）對帳不修任何一邊：兩個新檢查項在漂移時，呼叫前後檔案與 DB 列（事件除外）逐項相同。
  - Given 20-1、20-2 的漂移專案
  - When POST reconcile 三次
  - Then 檔案位元組與 mtime、DB 各表列數與雜湊（事件除外）不變；`state.json` 仍只被寫出、不被讀作輸入（沿 AT-960-21-5 的靜態判準，新模組納入掃描範圍）
  - 判定：python -m pytest tests/test_research_reconcile.py -k AT_961_20_E_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-22-1**（pytest｜`test_research_int_p1.py`｜Integration｜AC-R2P-12-1、AC-R2P-11-2、AC-R2P-11-7）整合鏈（軌道 A）：拋棄式 clone 上預演、確認、發佈、內環鍵採納、對帳，主工作樹零擾動，逐字證據。
  - Given 活 Bridge（`make_bridge`，研究根與 `BRIDGE_ALLOWED_PATH_ROOTS` 皆在暫存目錄）、`RDB`、真 `SDD_ROOT`（缺則 TOOL-ABSENCE，SCG-4 須 0 skipped）、TMPFSM、`GIT` 拋棄式 clone（來源取 §5.2 的兩種方式其一）；外環已走到 Gate 0 核准（以 mock 劇本 `pass` 跑完，不手寫 DB 列）
  - When POST route-preview；POST route（同步，200）；POST reconcile
  - Then 預演前後 `git status --porcelain`、worktree 清單、DB 列數相同（出口 (b)）；確認後 feature 分支、worktree、發佈檔、落點 stub 齊備、主工作樹 HEAD 與狀態不變（出口 (c)）；內環鍵 `show` 現態 SPEC_FROZEN、`frozen_stages[-1].stage` 為 `Stage-1`、PRD 摘要等於外環 Gate 0 摘要（出口 (d) 逐字貼證據）；路由列 `SUCCEEDED`、`impl_fsm_project` 與 `impl_state_dir` 入庫、`research_route_steps` 完整、游標 `build`／`ROUTED`；分流時點對帳 `consistent` 為真（出口 (h)）；全程假 gh 呼叫 0 筆
  - 判定：python -m pytest tests/test_research_int_p1.py -k AT_961_22_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-22-2**（pytest｜`test_research_int_p1.py`｜Integration｜AC-R2P-13-4、AC-R2P-11-2）整合鏈（軌道 B）：暫存 scaffold 根與假 gh 上走完新專案、複製、初始 commit 與遠端，token 零外洩。
  - Given 同 22-1 的活 Bridge；暫存 `BRIDGE_SCAFFOLD_ROOT`；`GH` 假 gh（本平台形態；§5.2）；假 token
  - When POST route 軌道 B（`create_github` 為真、`PRIVATE`）完成；POST reconcile；掃描全部落地面
  - Then 新專案根含四編號目錄完整副本、`.git`（初始 commit 一筆）、`.github/workflows/*`、`docker-compose.yml`、`.env.example`；`git ls-files` 不含 raw 與 `.env`；`GH` 呼叫序為 `auth status`、`repo create … --private --source . --push`；內環鍵 Stage-1 採納成功；token 全面掃描零命中（出口 (f)）；原工作區原地保留；分流時點對帳 `consistent` 為真（出口 (a)、(h)）
  - 判定：python -m pytest tests/test_research_int_p1.py -k AT_961_22_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-22-3**（pytest｜`test_research_int_p1.py`｜Integration｜AC-R2P-14-7、AC-R2P-11-7）整合鏈（拆解後 TCS 草擬）：接 22-1，先 :decompose（夾具引擎）再 tcs-draft 以 mock 劇本走完，內環 Stage-2 的 show 逐字證據。
  - Given 接 22-1 的專案；拆解引擎夾具；mock claude 劇本含 `(tcs-draft, 0)`；真 CLI（拆解列為 tcs-draft 前置，D-110）
  - When POST `:decompose`；POST tcs-draft:start 並等 stage 成功；讀內環鍵 `show`
  - Then TCS 發佈到目標 `docs/03_testing/contracts/`、`tcs_rel_path` 與 `tcs_sha256` 入庫；內環鍵現態 SPEC_DRAFTING（Stage-2）且 `decision_trace` 末筆為該 transition；`show` 全文逐字貼入證據（出口 (d)）；既有 `:freeze` 以 TCS 凍結成功後內環鍵為 SPEC_FROZEN 並含 Stage-2
  - 判定：python -m pytest tests/test_research_int_p1.py -k AT_961_22_3 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-22-4**（pytest｜`test_research_int_p1.py`｜Integration｜AC-R2P-19-8）整合鏈（SCR MINOR）：接 22-3 之後（內環已進入 IMPLEMENTATION 的夾具態），SCR 序列端到端，證據與人工等價序列一致。
  - Given 接 22-3 並以 `transition` 序列把內環鍵推進到 IMPLEMENTATION（夾具劇本，標明為夾具、非真實開發 run）；SCR（MINOR）
  - When POST `:scr`；走完 13-1 的序列
  - Then 序列、`impl_fsm_actions`、`decision_trace` 與 AT-961-13-1 的判準一致（出口 (g)）；證據標明為夾具態、不充當真實 SCR 演練（真實演練屬 P2 出口 (c)）
  - 判定：python -m pytest tests/test_research_int_p1.py -k AT_961_22_4 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-22-E-1**（pytest｜`test_research_int_p1.py`｜Integration｜AC-R2P-13-4）假 gh 夾具兩形態可行：本平台的假 gh 可被 gitops 以 PATH 解析並執行，記錄 argv 與環境鍵名。
  - Given `GH` 夾具：Windows 為 `gh.cmd`（轉呼叫 `python gh_fake.py`）、POSIX 為可執行 `gh`（sh 腳本）；PATH 前置
  - When 經 gitops 呼叫 `gh auth status` 與 `gh repo create …`
  - Then 解析到夾具而非真 gh（`shutil.which('gh')` 落在夾具目錄）；退出碼與輸出依夾具設定；記錄含 argv 與環境鍵名單；PowerShell 與 POSIX 兩形態的檔案皆入 `tests/fixtures/research/gh/`，只有本平台那一份在本機被實跑，另一平台標「未驗」（NFR-R2P-10-3）
  - 判定：python -m pytest tests/test_research_int_p1.py -k AT_961_22_E_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-22-E-2**（pytest｜`test_research_int_p1.py`｜Integration｜AC-R2P-12-1）拋棄式 clone 的兩種來源都可：git clone --no-hardlinks 與 git archive 匯出再 git init，分流最小路徑皆通過。
  - Given `GIT` 夾具兩種模式；各取本 repo 的 `HEAD`
  - When 各執行 AT-961-22-1 的預演與確認最小子集
  - Then 兩種來源皆建立 worktree 與分支、發佈檔 sha256 正確；`git archive` 版無歷史，基底 ref 取該 init 的 `main`；真 repo 的 `HEAD`、`git status --porcelain` 與 `git for-each-ref` 的摘要在整個測試前後不變（對真 repo 只讀；不比對 `.git` 位元組，以免多視窗並行工作時偶發失敗）
  - 判定：python -m pytest tests/test_research_int_p1.py -k AT_961_22_E_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-23-5**（pytest｜`test_cross_platform_guard.py`｜Integration｜AC-R2P-02-7）Bridge 全套與跨平台守衛：含新模組後全套綠且 0 skipped（DSN 與 SDD_ROOT 在場）。
  - Given `BRIDGE_TEST_DSN` 與 `SDD_ROOT` 皆在場；venv python
  - When `python -m pytest -q`（全套）；`tests/test_cross_platform_guard.py`、`test_research_capability.py`、`test_research_ast_locks.py` 單跑
  - Then 全套 rc 0、0 failed、0 skipped（摘要貼入證據）；三個守衛檔綠；新模組皆已登記
  - 判定：python -m pytest -q（cwd＝AgentConsole/engine-bridge；DB 與 SDD_ROOT 在場；讀 rc 先存變數）
- **AT-961-23-E-1**（pytest｜`test_research_int_p1.py`｜Integration｜AC-R2P-02-7）hermetic：AT 全程不連外部網路，假 gh 與假連線層取代真端點。
  - Given 把 `socket.create_connection` 與 `socket.getaddrinfo` 換成對非 loopback 目標丟錯的替身（`conftest` 級別，只在本 AT 啟用）
  - When 跑 22-1、22-2 的最小子集與 `test_research_route_b.py`
  - Then 全數通過；替身被呼叫（對外連線）的次數為 0；GitHub、PyPI、arXiv 等真端點在任何 AT 中都不被連線
  - 判定：python -m pytest tests/test_research_int_p1.py -k AT_961_23_E_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-25-2**（pytest｜`test_research_reconcile.py`｜Integration｜AC-R2P-14-7、AC-R2P-23-1）Bridge :reconcile 校正（D-125 之二）：TCS_PENDING 且內環已凍結 Stage-2 時，同交易把游標寫為 build／ROUTED／IDLE 並記 research.step 事件。
  - Given `LB`、`RDB`、TMPFSM 與真 CLI；專案游標 `build`／`TCS_PENDING`，內環鍵已經既有 `:freeze` 凍結 Stage-2（`frozen_stages` 含 `Stage-2`）
  - When POST `:reconcile` 兩次
  - Then 第一次：同一資料庫交易內游標改為 `build`／`ROUTED`／`IDLE`，並新增一筆 `research.step` 事件（payload 的 `reason` 為 `tcs_frozen_correction`）；`fsm_flow_mapping` 在校正前判「待校正」（`pending_correction`，不是 drift），回應 `consistent` 為真；第二次：無新事件、游標不變（冪等）；對帳仍不修改任何檔案；`state.json` 仍只被寫出
  - 判定：python -m pytest tests/test_research_reconcile.py -k AT_961_25_2 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）
- **AT-961-25-E-1**（pytest｜`test_research_reconcile.py`｜Integration｜AC-R2P-14-7、AC-R2P-23-1）負控：Stage-2 未凍結時不校正、不發事件、不衍生為 BUILD_READY。
  - Given TMPFSM；內環鍵現態 SPEC_DRAFTING、HUMAN_PENDING（TCS 待凍結）兩種，游標 `build`／`TCS_PENDING`；console-api 讀端同夾具
  - When POST `:reconcile`；讀專案詳情
  - Then 游標不變（仍 `TCS_PENDING`）、無 `tcs_frozen_correction` 事件、`fsm_flow_mapping` 為 `ok`（合法組合）；讀端 `effective` 不是 `BUILD_READY`；`research_events` 序號不變（對帳事件除外）
  - 判定：python -m pytest tests/test_research_reconcile.py -k AT_961_25_E_1 -q（cwd＝AgentConsole/engine-bridge；DB 型加 BRIDGE_TEST_DSN）

### 3.2 backend（JUnit；徑②）

- **AT-961-1-1**（JUnit｜`ResearchSchemaMigrationIT`｜Integration｜AC-R2P-02-7、AC-R2P-02-8）Flyway 歷史 1～19 全成功；V19 的五張表與一個視圖齊備且只在 console schema；ddl-auto validate 不報錯。
  - Given 套用 V1～V19 的 PostgreSQL 18 容器（Testcontainers）
  - When 讀 flyway_schema_history 與 information_schema（tables、views）；以 `ddl-auto=validate` 啟動應用內容
  - Then 版本依序為 1 至 19 且皆成功，V19 的描述含 `research route scr delivery`；console schema 恰多出 `research_route_decisions`、`research_route_steps`、`research_scr`、`research_decompositions`、`research_deliveries` 五表與視圖 `v_research_healing_attempts`；public schema 零新物件；啟動不因新表報 validate 錯；既有 `ResearchSchemaMigrationIT` 的 P0 斷言（`:495` 改釘 `databaseAt("18")` 對 P0 的十三張；`CONTROLLED_TABLES` 與 `RESEARCH_TABLES` 維持 P0 值）不退步，V19 增量由 `V19_TABLES` 五表與 `V19_CONTROLLED_TABLES` 四表另立斷言（`:518` 與 `:1385-1389` 的期望集合為 P0 集合加 V19 集合，§4 第 34 列）；V19 內五表的全部 `timestamp` 欄型別皆為 `timestamp with time zone`（AC-R2P-02-8；以 information_schema.columns 逐欄查，不得有 `timestamp without time zone`）
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_961_1_1*"（cwd＝AgentConsole/backend）
- **AT-961-1-2**（JUnit｜`ResearchSchemaMigrationIT`｜Integration｜AC-R2P-02-7）research_route_decisions 的 CHECK：軌道與目標種類與模組三者一致、列舉值、PUBLIC 只准軌道 B、狀態列舉。
  - Given 套用 V1～V19；一個合法研究專案列與一筆合法的軌道 A 路由列（`track=A`、`target_kind=MODULE`、`target_module=agentconsole`）
  - When 逐一插入違規列：`track` 為 `C`；軌道 A 配 `target_kind=STANDALONE`；軌道 A 缺 `target_module`；軌道 B 帶 `target_module`；軌道 B 配 `target_kind=MODULE`；`target_module` 為 `other`；`repo_visibility` 為 `INTERNAL`；軌道 A 配 `repo_visibility=PUBLIC`；`status` 為 `DONE`；`target_path` 為 NULL；`decided_by` 為 NULL；各列舉的合法值（`autoclaude`、`agentconsole`、`sdd`、`monorepo`；`PENDING`、`RUNNING`、`SUCCEEDED`、`FAILED`、`COMPENSATED`；`PUBLIC` 搭軌道 B）
  - Then 違規列一律被拒：CHECK 違反為 SQLSTATE 23514、NOT NULL 為 23502，錯誤訊息點出約束名；合法值全數通過；欄寬超界的值（`git_branch` 201 字元）構造為 22001 而非 23514（§5.1 越界值構造規則）；`published_docs` 預設 `{}`、`console_project_id` 外鍵指向不存在的專案為 23503
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_961_1_2*"（cwd＝AgentConsole/backend）
- **AT-961-1-3**（JUnit｜`ResearchSchemaMigrationIT`｜Integration｜AC-R2P-02-7）ux_research_route_active 部分唯一索引：同一研究專案至多一筆 PENDING、RUNNING 或 SUCCEEDED。
  - Given 套用 V1～V19；一個研究專案
  - When 依序：插入 `FAILED` 列兩筆；插入 `PENDING` 一筆；再插入 `RUNNING`；把該 `PENDING` 列更新為 `FAILED` 後再插入 `SUCCEEDED`；把它更新為 `COMPENSATED` 後再插入 `PENDING`；另一個研究專案插入 `PENDING`
  - Then 兩筆 `FAILED` 可並存；第二筆有效狀態列被拒（23505、訊息含 `ux_research_route_active`）；列離開有效狀態集合後可再插入新的有效列；不同研究專案互不影響；FAILED 與 COMPENSATED 列永不阻擋新分流（對應 PRD 的「部分失敗可重試」與「補償後可重新分流」）
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_961_1_3*"（cwd＝AgentConsole/backend）
- **AT-961-1-4**（JUnit｜`ResearchSchemaMigrationIT`｜Integration｜AC-R2P-02-7）research_route_steps 的 CHECK 與主鍵：十一個步驟名、五個狀態、步序下界、(route_id, step_no) 唯一。
  - Given 套用 V1～V19；一筆合法的路由列
  - When 插入 `step_no` 為 0、1、1（重複）；`step` 取十一個合法值（`VALIDATE_TARGET`、`GIT_SWITCH`、`SCAFFOLD_FILES`、`GIT_INIT`、`GIT_COMMIT`、`GH_REPO_CREATE`、`PUBLISH_DOCS`、`COPY_WORKSPACE`、`REGISTER_STUB`、`IMPL_KEY_INIT`、`BASELINE_ADOPT`）與 `GIT_PUSH`；`status` 取五個合法值與 `DONE`；`stdout_tail` 恰 2000 與 2001 字元；`route_id` 不存在
  - Then `step_no` 為 0 被拒（23514）、重複被拒（23505）；十一個合法步驟名與五個合法狀態皆通過、`GIT_PUSH` 與 `DONE` 被拒；2000 字元通過、2001 字元為 22001；孤兒 `route_id` 為 23503；`argv_redacted` 預設空字串
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_961_1_4*"（cwd＝AgentConsole/backend）
- **AT-961-1-5**（JUnit｜`ResearchSchemaMigrationIT`｜Integration｜AC-R2P-02-7）research_scr 的 CHECK 與唯一鍵：型別、來源類別、理由分類、狀態列舉與 (research_id, scr_no) 唯一。
  - Given 套用 V1～V19；一個研究專案
  - When 插入：`kind` 為 `MINOR`、`MAJOR`、`MEDIUM`；`source_kind` 四個合法值與 `OTHER`；`reason_class` 五個合法值（`EVIDENCE`、`AC_VAGUE`、`REQ_CHANGE`、`INFEASIBLE`、`OTHER`）與 `BUG`；`status` 五個合法值（`OPEN`、`APPROVED`、`REJECTED`、`APPLIED`、`SUPERSEDED`）與 `CLOSED`；`scr_no` 為 0 與 1 與重複的 1；省略 `reason_class`、`affected_sections`、`impl_fsm_actions`
  - Then 非法值皆 23514、`scr_no` 為 0 為 23514、重複 `scr_no` 為 23505；合法值通過；省略欄位時 `reason_class` 為 `OTHER`、`affected_sections` 為空陣列、`impl_fsm_actions` 為 JSON 空陣列；`requested_by` 為 NULL 為 23502
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_961_1_5*"（cwd＝AgentConsole/backend）
- **AT-961-1-6**（JUnit｜`ResearchSchemaMigrationIT`｜Integration｜AC-R2P-02-7）research_decompositions 的 CHECK：路徑、雜湊格式、任務數下界、七個狀態。
  - Given 套用 V1～V19；一個研究專案
  - When 插入：`path` 為 `A`、`B`、`C`、`D`；`tcs_sha256` 與 `prd_sha256` 為 64 位小寫十六進位、63 位、64 位含大寫、`NULL`；`tasks_count` 為 -1、0；`status` 七個合法值（`DRAFTED`、`SCG_PASSED`、`FROZEN`、`IMPORTED`、`SIGNED_OFF`、`REJECTED`、`STALE`）與 `DONE`；省略 `status`
  - Then `D`、63 位、大寫、-1、`DONE` 皆 23514；合法與 NULL 通過；省略 `status` 時為 `DRAFTED`、`tasks_count` 為 0；`import_record_id` 指向不存在列為 23503
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_961_1_6*"（cwd＝AgentConsole/backend）
- **AT-961-1-7**（JUnit｜`ResearchSchemaMigrationIT`｜Integration｜AC-R2P-02-7）research_deliveries：列舉、雜湊格式、(research_id, kind, ref) 唯一、append-only（P2 寫入，表於 P1 建立）。
  - Given 套用 V1～V19；一個研究專案
  - When 插入：`kind` 三個合法值與 `RELEASE_NOTES`；`status` 為 `CREATED`、`FAILED`、`PENDING`；`commit_sha` 為 40 位小寫十六進位與 39 位；同 (research_id, kind, ref) 兩次；對成功列做 UPDATE（任一欄）與 DELETE
  - Then 非法列舉與 39 位雜湊為 23514、重複為 23505；UPDATE 與 DELETE 一律被 append-only 守衛拒絕（SQLSTATE 23000、訊息含表名）；列內容不變
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_961_1_7*"（cwd＝AgentConsole/backend）
- **AT-961-1-8**（JUnit｜`ResearchSchemaMigrationIT`｜Integration｜AC-R2P-02-7）四張 V19 受控可更新表的通用守衛：清單內欄可更新、清單外欄位與任何 DELETE 被拒；含複合主鍵表的列定位（與 V16 函式內的允許清單逐表對拍；不併入 P0 的受控表迴圈）。
  - Given 套用 V1～V19；常數 `V19_CONTROLLED_TABLES`（四表：`research_route_decisions`、`research_route_steps`、`research_scr`、`research_decompositions`）各一列合法資料；V16 函式 `research_controlled_update_guard()` 的允許清單（以 `pg_get_functiondef` 讀出）；列定位方式：路由、SCR、拆解三表以 `id` 主鍵、`research_route_steps` 以複合主鍵 `(route_id, step_no)`（無 `id` 欄）；本 AT 自備列定位與欄位清單，**不使用** P0 的 `rowIds` 與 `CONTROLLED_UPDATE_COLUMNS`（那兩者只含 P0 五表，併入會 NPE）
  - When 對每張表更新「清單內」的每一欄（路由列：`status`、`failure_step`、`finished_at`、`repo_url`、`published_docs`、`console_project_id`、`impl_fsm_project`、`impl_state_dir`；步驟列：`status`、`exit_code`、`stdout_tail`、`stderr_tail`、`finished_at`；SCR 列：`status`、`prd_to_version_no`、`successor_research_id`、`impl_fsm_actions`、`decided_by`、`decided_at`；拆解列：`status`、`draft_id`、`import_record_id`、`tcs_rel_path`、`tcs_sha256`、`tasks_count`、`gate_rejection`）；再更新「清單外」代表欄（路由列的 `track`、`target_path`、`scope_differs_reason`、`decided_by`；步驟列的 `step`、`argv_redacted`；SCR 列的 `reason`、`kind`、`requested_by`；拆解列的 `prd_sha256`、`path`、`created_by`）；對四表各做 DELETE
  - Then 四表皆被覆蓋（斷言 `V19_CONTROLLED_TABLES` 恰四表且與守衛函式的 V19 條目逐表相等）；清單內每欄更新成功（參數化，失敗訊息指出表與欄；步驟表以 `(route_id, step_no)` 定位更新）；清單外代表欄一律 23000 且訊息含表名與允許欄清單；DELETE 一律被拒；斷言取用的欄位清單與 V16 函式內的字面清單相等（只讀函式定義，不手抄第二份）；`research_deliveries` 不在受控清單（它是 append-only，見 1-7）
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_961_1_8*"（cwd＝AgentConsole/backend）
- **AT-961-1-9**（JUnit｜`ResearchSchemaMigrationIT`｜Integration｜AC-R2P-02-7）視圖 v_research_healing_attempts：只含 RETRYING 與 FAILED 步驟、經 console_project_id 連結、不提供任何寫入路徑。
  - Given 套用 V1～V19；一個研究專案綁定一個 Console 專案、該專案一筆執行 run、四筆步驟（狀態 `SUCCESS`、`RETRYING`、`FAILED`、`PENDING`）；另一個未綁定 Console 專案的研究專案
  - When 查視圖；對視圖做 INSERT、UPDATE、DELETE
  - Then 視圖欄位恰為 research_id、run_id、run_number、task_id、step_number、action、status、error_message、tokens_used、occurred_at；只回 `RETRYING` 與 `FAILED` 兩筆且 `research_id` 為綁定的那個專案；未綁定專案零列；INSERT、UPDATE、DELETE 皆被資料庫拒絕（視圖含 join 而不可更新，不得有任何 INSTEAD OF 觸發器或規則：`pg_trigger` 與 `pg_rules` 對該視圖為零）
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_961_1_9*"（cwd＝AgentConsole/backend）
- **AT-961-1-E-1**（JUnit｜`ResearchSchemaMigrationIT`｜Integration｜AC-R2P-02-7）所有十八張 research_ 表（P0 十三張加 V19 五張）逐表 DELETE 一律被擋，守衛錯誤的 SQLSTATE 一律為類別 23。
  - Given 套用 V1～V19；每張表至少一列（P0 十三張沿既有夾具、V19 五張以 1-2 至 1-7 的合法列）
  - When 對每張 `console.research_*` 表（表清單取 information_schema，不手抄）做 DELETE
  - Then 表清單恰十八張；每次 DELETE 皆被拒、SQLSTATE 類別為 23（`integrity_constraint_violation`）、訊息含表名；刪除前後列數相同；新增第十九張而未掛守衛時本 AT 紅（以表清單與守衛掛載清單相減為空斷言）
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_961_1_E_1*"（cwd＝AgentConsole/backend）
- **AT-961-1-E-2**（JUnit｜`BackupJobMigrationIT`｜Integration｜AC-R2P-02-7）既有五個 Flyway IT 的版本清單改為 1 至 19，且 BackupJobMigrationIT 的「既有表零變動」快照把視圖排除。
  - Given 既有 `SchemaMigrationIT`、`V5UpgradeMigrationIT`、`IssuePriorityMigrationIT`、`BackupJobMigrationIT`、`SiConsoleWritesMigrationIT`、`ResearchSchemaMigrationIT`（§4 第 1 列）
  - When 各自跑 `flyway_schema_history` 版本斷言與升級前後快照；快照欄位查詢把 `v_research_healing_attempts` 與 `research_` 起頭之表都排除
  - Then 六處版本清單皆為 `"1"` 至 `"19"`；`snapshotOfExistingTables` 前後相等（既有 console 表與其約束零變動）；欄位查詢確實排除視圖（information_schema.columns 含視圖欄位，不排除則升級後快照多出 10 欄而紅；本 AT 以「還原排除條件則失敗」的突變驗證其鑑別力）；約束查詢維持 `conrelid::regclass::text not like 'console.research\\_%'`（V19 五表的約束已被它排除，視圖沒有約束）
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.persistence.BackupJobMigrationIT.AT_961_1_E_2*"（cwd＝AgentConsole/backend）
- **AT-961-1-E-3**（JUnit｜`ResearchSchemaMigrationIT`｜Integration｜AC-R2P-02-7）V19 的預設值與 JSONB 欄位型別：published_docs 預設 {}、impl_fsm_actions 預設 []、型別皆為 jsonb。
  - Given 套用 V1～V19
  - When 查 information_schema 的 `data_type` 與 `column_default`；插入省略這些欄位的列後讀回；對 `impl_fsm_actions` 寫入非陣列 JSON
  - Then 兩欄型別為 `jsonb`；預設分別為 `'{}'::jsonb` 與 `'[]'::jsonb`；省略時讀回 `{}` 與 `[]`；`impl_fsm_actions` 的更新屬受控清單內（1-8），內容形狀（陣列）由 Bridge 寫入器保證——DDL 不擋非陣列，本 AT 以註記斷言「DDL 不擋、應用層擋」（Architecture K.4 的 DDL 驗收段未要求此 CHECK；列 ⚖P1-9）
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_961_1_E_3*"（cwd＝AgentConsole/backend）
- **AT-961-11-1**（JUnit｜`ResearchDecompositionApiIT`｜Integration｜AC-R2P-14-3、AC-R2P-14-2）簽核：OPERATOR 以上對 POST decomposition/signoff 送出，經既有 import／signoff 服務（不走 HTTP 迴圈）落為正式專案、目標、任務並關聯研究專案。
  - Given 迷你 Bridge 回放黃金檔（拆解草稿、覆蓋全滿）；`AbstractApiIT`；OPERATOR 憑證；一個研究專案綁定 Console 專案
  - When POST `/api/v1/research/projects/{id}/decomposition/signoff`（approver 取 JWT subject；`waivers[]` 選填）；另一次覆蓋不全且無豁免時 POST
  - Then 回 200；正式 `goals`、`tasks` 落庫、數量等於已簽核版本、`signed_off` 為真、`signed_off_by` 為 JWT subject、`signed_off_at` 帶時區；console-api 呼叫 Bridge `:decomposition-signoff`（一次寫 `SIGNED_OFF` 與 `import_record_id`，D-113）；覆蓋不全且無豁免回 422 `invalid_request`（`violations[{field: coverage, rule: uncovered_ac}]`，列出未覆蓋 AC），零落庫、迷你 Bridge 無簽核請求
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchDecompositionApiIT.AT_961_11_1*"（cwd＝AgentConsole/backend）
- **AT-961-11-2**（JUnit｜`ResearchDecompositionApiIT`｜Integration｜AC-R2P-14-3）簽核的角色與輸入：approver 取 JWT subject；憑證無 subject 回 400、VIEWER 403、匿名 401、ADMIN 同 OPERATOR；本文帶 approver 不被採用。
  - Given 同 11-1；四種憑證與一個缺 approver 的請求
  - When 各 POST 簽核：OPERATOR、ADMIN、VIEWER、匿名各一次；以夾具造一張 subject 為空字串的 OPERATOR JWT 呼叫；本文帶 `approver: "mallory"` 的一次
  - Then 憑證無 subject（空字串）400（不是「本文缺 approver」：approver 不由本文取）；VIEWER 403 `ACCESS_DENIED`；匿名 401；ADMIN 200；每個被拒請求迷你 Bridge 請求數為 0、零落庫；本文帶 `approver` 鍵被忽略（`signed_off_by` 仍為 JWT subject，不被改寫）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchDecompositionApiIT.AT_961_11_2*"（cwd＝AgentConsole/backend）
- **AT-961-11-3**（JUnit｜`ResearchDecompositionApiIT`｜Integration｜AC-R2P-14-4）未簽核草稿啟動執行回 409，execute、resume、restore 三個入口皆二次校驗，前端停用只是體驗。
  - Given `AbstractApiIT`；綁定研究專案的 Console 專案，其拆解草稿 `signed_off` 為假；OPERATOR 憑證
  - When POST 既有 `execute`、`resume`、`restore` 啟動入口（路徑取既有 ExecutionController）
  - Then 三者皆 409，訊息為既有 US-E-01 的「草稿未經人工審批，禁止執行」（逐字沿用，不新增 reason）；`execution_runs` 零新列；迷你 Bridge 的 `/autoclaude/runs` 請求數為 0；簽核後同請求通過
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchDecompositionApiIT.AT_961_11_3*"（cwd＝AgentConsole/backend）
- **AT-961-11-4**（JUnit｜`ResearchDecompositionApiIT`｜Integration｜AC-R2P-14-5）拆解 stale 時啟動執行回 409 decomposition_stale（console-api 側只驗 409 與透傳形狀；STALE 的寫入歸 Bridge 側 AT-961-10-5）。
  - Given 已簽核的拆解，其 `prd_sha256` 與研究專案現行凍結摘要不符（以 `research_gate_decisions` 新增 SCR 版模擬）
  - When POST 啟動執行；重新拆解並簽核後再 POST
  - Then 前者 409 `decomposition_stale`（`details.expected_sha256`、`details.actual_sha256`，取自迷你 Bridge 或 DB 夾具的回應形狀並逐字透傳）、零 `execution_runs` 列、Bridge 無啟動請求；重新拆解並簽核後同請求放行；console-api 以讀取時比對判定，不寫任何研究表（`status` 為 `STALE` 的寫入由 Bridge 完成並由 AT-961-10-5 驗，本 AT 不斷言）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchDecompositionApiIT.AT_961_11_4*"（cwd＝AgentConsole/backend）
- **AT-961-11-5**（JUnit｜`ResearchDecompositionApiIT`｜Integration｜AC-R2P-14-4）SCR 開啟期間啟動執行回 409 scr_open，內環唯讀。
  - Given 研究專案有一筆 `OPEN` 的 `research_scr`；已簽核的拆解
  - When POST 啟動執行與恢復執行
  - Then 皆 409 `scr_open`；`execution_runs` 零新列；迷你 Bridge 無啟動請求；SCR 轉 `APPLIED` 或 `REJECTED` 後放行
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchDecompositionApiIT.AT_961_11_5*"（cwd＝AgentConsole/backend）
- **AT-961-11-6**（JUnit｜`ResearchDecompositionApiIT`｜Integration｜AC-R2P-14-7）TCS 未凍結時內環 run 啟動回 409 fsm_state_conflict（D-102：既有啟動服務的單一前置守衛），凍結後放行。
  - Given 已簽核拆解；內環鍵 FSM 視圖（迷你 Bridge `GET /sdd/fsm`）：現態 SPEC_DRAFTING（Stage-2 未凍結）與 SPEC_FROZEN 且 `frozen_stages` 含 Stage-2 兩種
  - When POST 啟動執行
  - Then 前者 409 `fsm_state_conflict`（`details.current_state`、`details.expected` 為內環鍵含 Stage-2 凍結；不新增 reason）、零啟動；後者放行；判準取內環鍵 FSM 視圖的 `frozen_stages`（不取 DB 旗標、不自行維護第二份狀態）；三個守衛（`scr_open`、`decomposition_stale`、TCS 未凍結）的檢查序固定為 `scr_open`、`decomposition_stale`、`fsm_state_conflict`，先中者定案
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchDecompositionApiIT.AT_961_11_6*"（cwd＝AgentConsole/backend）
- **AT-961-11-7**（JUnit｜`ResearchDecompositionApiIT`｜Integration｜AC-R2P-14-1）POST decomposition（觸發）：OPERATOR 以上、Bridge 同步呼叫讀逾時 330 秒、422 結構化錯誤逐字透傳，VIEWER 403。
  - Given `AbstractApiIT`；迷你 Bridge 回放 200（含 coverage）、422 `invalid_request`（`violations[].rule` 為 `max_steps`）、409 `scr_open`；`BridgeHttpAdapter` 的逾時表
  - When POST `/api/v1/research/projects/{id}/decomposition`（VIEWER、OPERATOR、匿名各一次）；以假時鐘讀逾時
  - Then OPERATOR 200（`data` 含 `decompositionId`、`status`、`tasksCount`、`coverage`）；VIEWER 403 `ACCESS_DENIED`、匿名 401；Bridge 422／409 狀態碼、reason 與 `details` 逐字透傳；讀逾時為 330 秒（`route` 與 `decomposition` 兩個 Bridge 呼叫，D-105；其餘研究寫入仍為 30 秒）；POST 不重試（迷你 Bridge 請求數恰 1）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchDecompositionApiIT.AT_961_11_7*"（cwd＝AgentConsole/backend）
- **AT-961-11-E-1**（JUnit｜`ResearchDecompositionApiIT`｜Integration｜AC-R2P-14-3）軌道 B 的 Console 專案 execution_path 為新專案根，須在 allowlist 根之下，否則建專案被拒。
  - Given route 確認路徑（AT-961-14-3）；`execution_path` 為 allowlist 內與 allowlist 外兩種
  - When POST route 軌道 B
  - Then allowlist 外 422 `sanitization_failed`、零 `projects` 列、Bridge 請求數 0；allowlist 內通過
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchDecompositionApiIT.AT_961_11_E_1*"（cwd＝AgentConsole/backend）
- **AT-961-11-E-2**（JUnit｜`ResearchDecompositionApiIT`｜Integration｜AC-R2P-14-4）回歸：非研究專案的 Console 專案啟動執行完全不受 D-102 前置守衛影響。
  - Given `AbstractApiIT`；一個未被任何 `research_projects.console_project_id` 引用的專案（已簽核、有或沒有 TCS）
  - When POST 既有 execute、resume、restore
  - Then 行為與守衛加入前逐位元相同（既有 execute 相關測試零改動仍綠）；守衛只在 `research_projects.console_project_id` 命中時才查 SCR、拆解與 FSM 視圖（迷你 Bridge 的 `/sdd/fsm` 請求數為 0）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchDecompositionApiIT.AT_961_11_E_2*"（cwd＝AgentConsole/backend）
- **AT-961-14-1**（JUnit｜`ResearchRouteApiIT`｜Integration｜AC-R2P-11-2、AC-R2P-11-6）route/preview：OPERATOR 以上、輸入閘先於 Bridge、Bridge 的缺項 422 逐字透傳。
  - Given `AbstractApiIT`；迷你 Bridge（記錄請求、可回放 200 動作清單與 422 `route_unsupported_in_deployment`）；VIEWER、OPERATOR、ADMIN 憑證；一個 Gate 0 後的研究專案
  - When POST `/api/v1/research/projects/{id}/route/preview`：合法本文；`branchName` 為 `feature/Bad`；`repoName` 為 1 字元；`visibility` 為 `INTERNAL`；`scopeDiffersReason` 201 字元；VIEWER 與匿名各一次；迷你 Bridge 回放 422 缺項
  - Then 合法：200，`data.actions[]` 逐項含 `seq`、`action`、`step`、`target`、`touchesExternal`、`detail`（camelCase；來自 Bridge snake_case 的轉換），另含 `executionPath`、`implStateDir`、`implFsmProject`、`expectedTrackedFiles[]`、`warnings[]`、`prd`；違規本文 400（`errors[]` 欄位級）且迷你 Bridge 請求數為 0；VIEWER 403 `ACCESS_DENIED`、匿名 401；Bridge 回 422 `route_unsupported_in_deployment` 時 console-api 回 422 同 reason 且 `details.missing[]` 逐字透傳；預演不寫任何 DB 列（D-108：所有 `research_*` 表與 `projects` 前後列數相同；`audit_log` 一列為橫切、不計）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchRouteApiIT.AT_961_14_1*"（cwd＝AgentConsole/backend）
- **AT-961-14-2**（JUnit｜`ResearchRouteApiIT`｜Integration｜AC-R2P-11-8）route 確認僅 ADMIN：OPERATOR 與 VIEWER 皆 403，Bridge 請求數 0、projects 列 0。
  - Given 同 14-1；各角色與匿名
  - When POST `…/route`（合法本文）
  - Then OPERATOR 403 `ACCESS_DENIED`（SecurityConfig 的精確路徑規則，P0 已預置；§4 第 6 列註明 `route` 規則不需改）、VIEWER 403、匿名 401；ADMIN 通過授權；被拒請求迷你 Bridge 請求數為 0、`projects` 列數不變、`research_route_decisions` 無新列；`…/route/preview` 不在 ADMIN 規則內（OPERATOR 可呼叫，沿 14-1）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchRouteApiIT.AT_961_14_2*"（cwd＝AgentConsole/backend）
- **AT-961-14-3**（JUnit｜`ResearchRouteApiIT`｜Integration｜AC-R2P-11-8、AC-R2P-12-4）先建 projects 列再呼 Bridge：順序可觀察，execution_path 取自預演回應，同 (execution_path, sdd_project) 只能綁一個專案。
  - Given 迷你 Bridge 於收到 `:route` 請求的當下查 `projects` 表（鉤子）；ADMIN 憑證；軌道 A 與軌道 B 各一個研究專案；另一個已綁定同 (execution_path, sdd_project) 的既有專案
  - When POST `…/route`（軌道 A、B 各一次；console-api 先呼 Bridge 預演取得 `executionPath`、`implFsmProject`）；另 POST 一個會綁到既有 (execution_path, sdd_project) 的請求
  - Then 迷你 Bridge 收到 `:route` 請求時 `projects` 列已存在（`execution_path` 為預演回應的 `executionPath`、`sdd_project` 為 `implFsmProject`、`signed_off` 為假、狀態 DRAFT）；請求本文帶該列的 `console_project_id`；重綁同一組合回 409（V12 唯一索引，reason 取既有專案綁定衝突碼）且迷你 Bridge 的 `:route` 請求數為 0、未新增 `projects` 列；成功回 200（同步，D-105）`RouteDecisionDto` 含 `publishedDocs`
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchRouteApiIT.AT_961_14_3*"（cwd＝AgentConsole/backend）
- **AT-961-14-4**（JUnit｜`ResearchRouteApiIT`｜Integration｜AC-R2P-11-8）失敗補償到安全態：projects 列標 ARCHIVED 並留稽核，不自動清理，且 Bridge 請求紀錄不含清理類呼叫。
  - Given 迷你 Bridge 分別回放：502 `route_step_failed`（`failureStep` 為 `GIT_SWITCH`）、連線失敗、讀取逾時；ADMIN 憑證
  - When POST `…/route` 三次（每次一個新專案）；補償完成後觀察 console-api 對 Bridge 的 `:route-compensated` 呼叫
  - Then `bridge_unreachable` 與 `bridge_timeout` 依既有映射回 502 與 504，`route_step_failed` 回 502 並帶 `failureStep`；三者之後先前建的 `projects` 列 `status` 為 `ARCHIVED`（不刪列）並有稽核（`AuditTrail.note("research.route.compensate", …)`，`audit_log` 一列）；補償完成後 console-api 呼叫 Bridge `POST …:route-compensated {route_id, reason, requested_by}`（D-112），Bridge 驗該列為 `FAILED` 才改 `COMPENSATED`；列非 `FAILED`（例如逾時但 Bridge 仍 `RUNNING`）時 Bridge 回 409 `route_conflict`，console-api 仍保持專案列 `ARCHIVED` 並記錄、不重試、不隱瞞；迷你 Bridge 請求紀錄只有 `:route`、`:route-compensated` 與唯讀請求，無任何清理、stash、刪目錄請求；POST 不重試（沿 BridgeHttpAdapter 語意）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchRouteApiIT.AT_961_14_4*"（cwd＝AgentConsole/backend）
- **AT-961-14-5**（JUnit｜`ResearchRouteApiIT`｜Integration｜AC-R2P-11-8）route_conflict 先於建專案列：已有 PENDING、RUNNING、SUCCEEDED 的分流回 409，零 projects 寫入。
  - Given 三個專案之路由列分別為 `PENDING`、`RUNNING`、`SUCCEEDED`（預先插入）；另一專案為 `FAILED`；ADMIN 憑證
  - When 各 POST `…/route`
  - Then 前三者 409 `route_conflict`、零 `projects` 新列、迷你 Bridge 請求數 0；`FAILED` 者允許（視為重試，沿用既有 `projects` 列而不再建新列：以 `execution_path` 與 `sdd_project` 查既有列復用）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchRouteApiIT.AT_961_14_5*"（cwd＝AgentConsole/backend）
- **AT-961-14-6**（JUnit｜`ResearchRouteApiIT`｜Integration｜AC-R2P-13-4）GitHub token：取自 system_configs 加密欄，單次請求傳給 Bridge，不入 DTO、回應、日誌、audit_log 與 toString。
  - Given 後端設定鍵 `research.github_token`（加密欄、預設空、登記於設定鍵目錄，D-98；不加 DDL）存有假 token `ghp_FAKE…`（經 `CONSOLE_ENCRYPTION_KEY` 加密）；迷你 Bridge 記錄請求本文；軌道 B、`createGithub` 為真；另一組 `createGithub` 為假；另一組鍵為空
  - When POST `…/route`；掃描全部 HTTP 回應、應用日誌擷取、`audit_log` 全欄、`projects` 與 `research_*` 全部文字欄、各 DTO 與 Request 物件的 `toString()`
  - Then `createGithub` 為真且鍵有值：迷你 Bridge 請求本文含 `github_token`（僅此一處；記憶體中單次傳遞）；`createGithub` 為假：本文不含 `github_token` 鍵（console-api 只在 `route` 且 `createGithub=true` 時放入，D-98）；鍵為空且 `createGithub` 為真：本文不含 `github_token` 且 console-api 不預先阻擋（由 Bridge 步驟失敗並說明，沿 AT-961-6-8）；其餘所有掃描面對假 token 零命中；掃描器有負控且範圍非空
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchRouteApiIT.AT_961_14_6*"（cwd＝AgentConsole/backend）
- **AT-961-14-7**（JUnit｜`ResearchRouteApiIT`｜Integration｜AC-R2P-11-3、AC-R2P-12-4）GET route：回 RouteDecisionDto 與 steps，V+ 可讀，無分流時回空而非 404。
  - Given 迷你 Bridge／DB 夾具：有一筆 `SUCCEEDED` 的路由與十一步以內的步驟列；另一專案尚無路由；三種角色
  - When GET `…/route`
  - Then 有路由：200，欄位逐一對應契約 §1.3 `RouteDecisionDto`（`routeId`、`track`、`targetKind`、`targetModule`、`targetPath`、`gitBranch`、`baseRef`、`repoUrl`、`repoVisibility`、`stackTemplate`、`consoleProjectId`、`implFsmProject`、`status`、`failureStep`、`steps[]`，另加 `publishedDocs`；契約勘誤 D-106）；`steps[]` 逐項為 `RouteStepDto`（`argvRedacted` 等）；無路由：200 且 `data` 為 null（D-106）；VIEWER 可讀；研究專案不存在 404 `research_not_found`；console-api 對 `research_*` 零寫入
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchRouteApiIT.AT_961_14_7*"（cwd＝AgentConsole/backend）
- **AT-961-14-8**（JUnit｜`ResearchRouteApiIT`｜Integration｜AC-R2P-11-3）route 與 decomposition 的 Bridge 呼叫讀逾時為 330 秒（Bridge 牆鐘上限 300 秒＋緩衝，D-105），其餘寫入呼叫維持 30 秒；Bridge 牆鐘逾時回 502 route_step_failed 而非 504 的語意。
  - Given `BridgeHttpAdapter` 的逾時設定；迷你 Bridge 可延遲回應；假時鐘
  - When 對 `route`、`decomposition`、`scr`、`approve` 各呼叫並讓迷你 Bridge 分別延遲到 30、31、330、331 秒（假時鐘）
  - Then `route`、`decomposition`：30 秒與 330 秒內回應皆正常取得、331 秒回 504 `bridge_timeout`；`scr`、`approve`：30 秒內回應正常、31 秒即 504；連線逾時仍為 2 秒；nginx 設定不改（`docker/nginx/conf.d/console-locations.inc` 的 `/api/` 既有讀逾時 86400 秒，本檔只引用不改）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchRouteApiIT.AT_961_14_8*"（cwd＝AgentConsole/backend）
- **AT-961-14-E-1**（JUnit｜`ResearchRouteApiIT`｜Integration｜AC-R2P-11-4）scopeDiffersReason 在 console-api 先判：軌道與 PRD target_scope 不同而缺理由回 422，相同時不要求。
  - Given 兩專案 `target_scope` 為 `AISDLC_MODULE` 與 `STANDALONE_PROJECT`；ADMIN
  - When POST `…/route` 與 preview 各組合
  - Then 不同且缺理由 422 `invalid_request`（規則 `scope_differs_reason_required`）、迷你 Bridge 請求數 0；有理由（1 至 200 字）放行並轉傳；相同不要求；判準與 Bridge 同一常數與函式語意（以黃金檔對拍）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchRouteApiIT.AT_961_14_E_1*"（cwd＝AgentConsole/backend）
- **AT-961-14-E-2**（JUnit｜`ResearchRouteApiIT`｜Integration｜AC-R2P-11-3）approver 只取 JWT subject：請求本文帶 approver 不被採信；欄位轉換 camelCase 與 snake_case 完整。
  - Given ADMIN 憑證（subject 為 `alice@example.com`）；迷你 Bridge 記錄請求本文
  - When POST `…/route`，本文帶 `approver: "mallory"`
  - Then 迷你 Bridge 收到的 `approver` 為 `alice@example.com`；請求鍵皆為 snake_case（`target_module`、`branch_name`、`base_ref`、`repo_name`、`confirm_repo_name`、`stack_template`、`create_github`、`console_project_id`、`scope_differs_reason`），回應鍵皆為 camelCase
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchRouteApiIT.AT_961_14_E_2*"（cwd＝AgentConsole/backend）
- **AT-961-15-1**（JUnit｜`ResearchScrApiIT`｜Integration｜AC-R2P-19-1、AC-R2P-19-5）POST scr 與 GET scr：角色、輸入閘、MINOR 與 MAJOR 回應、HEALING_FAILED 的指令回應。
  - Given `AbstractApiIT`；迷你 Bridge；VIEWER、OPERATOR、ADMIN 憑證；一個已分流的研究專案
  - When POST `…/scr`：合法 MINOR（console-api 先呼既有 stop 用例再呼 Bridge `:scr`，D-103）；`kind` 為 `MEDIUM`；`sourceKind` 為 `OTHER`；理由 501 字元；`affectedSections` 含空字串；VIEWER；MAJOR；`sourceKind` 為 `HEALING_FAILED`。GET `…/scr`
  - Then 合法 MINOR 202（OPERATOR 即可）且迷你 Bridge／stop 用例的呼叫序為「先 stop、後 `:scr`」（`HEALING_FAILED` 例外：不 stop）；`kind`、`sourceKind` 值域違規 400（`errors[]`）、迷你 Bridge 請求數 0；理由超界 400；VIEWER 403；MAJOR 回應含 `successorResearchId`；`HEALING_FAILED` 回應含 `recovery`（`target`、`powershell`、`posix`）；GET 回 `ScrDto[]`（欄位對應契約 §1.3，另加 `reasonClass`、`implFsmActions`）依 `scrNo` 遞增；Bridge 的 422 `violations[]`、409 `scr_open`／`scr_limit` 逐字透傳
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchScrApiIT.AT_961_15_1*"（cwd＝AgentConsole/backend）
- **AT-961-15-2**（JUnit｜`ResearchDecompositionApiIT`｜Integration｜AC-R2P-14-1、AC-R2P-14-5）GET decomposition：回 DecompositionDto（IFACE §3.1）：有效拆解、覆蓋、豁免與 stale 旗標，無拆解回 200 null，V+ 可讀。
  - Given DB 夾具：甲專案有 `SIGNED_OFF` 的拆解且 `prd_sha256` 等於現凍結摘要；乙專案拆解已 `STALE`；丙專案無拆解；VIEWER 憑證
  - When GET `…/decomposition`
  - Then 甲：200，含 `id`、`status`、`tasksCount`、`prdSha256`、`stale` 為假、`coverage`（`total`、`covered`、`uncovered[]`）、`tcs{relPath, sha256}`、`goals[]`、`waivers[]`；乙：`stale` 為真；丙：200 且 `data` 為 null（D-120：與 `GET …/route` 同一慣例，不用 `status: NONE`）；有效版取「已簽核且摘要相符的最新版」（沿 AT-961-10-7）；console-api 零寫入
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchDecompositionApiIT.AT_961_15_2*"（cwd＝AgentConsole/backend）
- **AT-961-15-3**（JUnit｜`OpenApiIT`｜Contract｜AC-R2P-14-1、AC-R2P-19-1）OpenAPI：P1 新增 6 條路徑與 9 個操作（總數 107 條路徑、124 個操作），operationId 與契約一致，回應碼表補列；數字由實際新增路徑與操作自算。
  - Given `OpenApiIT` 的 `EXPECTED`、`EXPECTED_PATH_COUNT`（現值 101，`:163`）、`EXPECTED_OPERATION_COUNT`（現值 115，`:164`）、研究路徑斷言（現值 24，`:944`）、`RESEARCH_OPERATION_IDS`（現值 25，`:953`）、`RESEARCH_STATUS_CODES`（現值 26，`:972`）
  - When 取 `/v3/api-docs` 並比對
  - Then 自算法：新增路徑＝`…/route/preview`、`…/route`、`…/scr`、`…/scr/{scrNo}/apply`、`…/decomposition`、`…/decomposition/signoff` 共 6 條（同路徑的 GET 與 POST 合併計一條），101＋6＝107；新增操作＝`previewResearchRoute`（POST）、`routeResearchProject`（POST）、`getResearchRoute`（GET）、`openResearchScr`（POST）、`listResearchScr`（GET）、`applyResearchScr`（POST）、`getResearchDecomposition`（GET）、`triggerResearchDecomposition`（POST）、`signoffResearchDecomposition`（POST）共 9 個，115＋9＝124（九個 operationId 為 D-118 定案）；研究路徑 24＋6＝30、有 operationId 的研究操作 25＋9＝34、研究操作回應碼表 26＋9＝35 項；每個新操作的 403、404、409、422、502 說明文字列出本端點可能的 reason（`ResearchErrorDocs` 的 EXTRA 表補列）；`stages/{stage}` 的 `allowableValues` 仍含 `tcs-draft`，其說明不再寫「尚未實作」（`ResearchController.java:224-226` 文字同步訂正，§4）；若實際新增數與自算不符，以實際為準並於證據註明差異來源
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.config.OpenApiIT.AT_961_15_3*"（cwd＝AgentConsole/backend）
- **AT-961-15-4**（JUnit｜`ResearchReasonsTest`｜Contract｜AC-R2P-19-1、AC-R2P-19-6、AC-R2P-14-5）reason 四處集合相等：P0 的 22 個、P0 未結 R-2 的 4 個、P1 的 9 個（共 35 個），後端常數、前端 RESEARCH_REASONS、契約、Architecture 研究 reason 表、OpenAPI 說明一致。
  - Given `ResearchReasonsTest` 的 `P0_REASONS`（22）；R-2 集合 `P0_TAIL_REASONS`：`compile_failed`（503）、`sdd_cli_failed`（502）、`fsm_state_unreadable`（422）、`invalid_request`（422；現為 console-api 區域常數，納入後改用 `RESEARCH_` 前綴常數，⚖P1-25）；P1 新增集合 `P1_REASONS`：`route_unsupported_in_deployment`（422）、`branch_exists`（409）、`target_not_empty`（422）、`public_confirmation_required`（422）、`route_conflict`（409）、`route_step_failed`（502）、`scr_open`（409）、`scr_limit`（409）、`decomposition_stale`（409）；TCS 未凍結不新增 reason（D-102 用既有 `fsm_state_conflict`）
  - When 後端 `ErrorReasons` 的 `RESEARCH_` 前綴常數、前端 `RESEARCH_REASONS` 區塊、契約 §0.2 與 §1.4 的反引號 reason、Architecture §11.1 研究 reason 表（含狀態碼）、`ResearchErrorDocs` 全文逐一比對；對 `lib/api/reasons.ts` 與 `API_Contract_P3-6.md` 附錄 B 做不污染檢查
  - Then 四處集合皆等於 `P0_REASONS ∪ P0_TAIL_REASONS ∪ P1_REASONS`（35）；Architecture 表的狀態碼與上列括號一致；每個 P1 reason 至少被一個 OpenAPI 端點說明提到；`lib/api/reasons.ts` 不含任何研究 reason（既有 `reasons.test.ts` 零改動仍綠）；退役的 `spec_digest_changed` 仍無處可尋；`ErrorReasons` 常數一律 `RESEARCH_` 前綴（`IssueReasonsContractTest`、`BackupReasonsContractTest` 的集合鎖不紅，§4）；本 AT 與前端 `RESEARCH_REASONS` 的 +9 同批落地（PACKAGES §3：FE-D1 只加前端內容、不跑該 JUnit，API-P1 改測試與後端常數）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchReasonsTest.AT_961_15_4*"（cwd＝AgentConsole/backend）
- **AT-961-15-5**（JUnit｜`ResearchArchTest`｜Contract｜AC-R2P-14-1、AC-R2P-14-5）ArchUnit 字串掃描：console-api 對 research_ 與 V19 表零寫入，新讀配接器只用 JdbcClient 查詢。
  - Given `adapter.out.persistence.research..` 套件（含 P1 新增的 Route、Scr、Decomposition 讀配接器）與 `application.service.Research*`
  - When 以字串掃描 SQL 字面值與 ArchUnit 規則
  - Then 套件內零 `INSERT`、`UPDATE`、`DELETE`、`MERGE`、`TRUNCATE` 字樣；新讀配接器無 JPA 實體；console-api 不 import Bridge 的 Python 路徑常數；對 `console.research_route_decisions`、`research_route_steps`、`research_scr`、`research_decompositions`、`research_deliveries` 的任何寫入語句為 0（console-api 只寫自己的 `projects` 列與 `audit_log`）；掃描器負控與非空範圍
  - 判定：gradlew test --tests "com.aisdlc.console.architecture.ResearchArchTest.AT_961_15_5*"（cwd＝AgentConsole/backend）
- **AT-961-15-6**（JUnit｜`RbacIT`｜Integration｜AC-R2P-19-1、AC-R2P-14-1）角色矩陣：route 與 scr/apply 僅 ADMIN；route/preview、scr、decomposition、decomposition/signoff 為 OPERATOR 以上；三個 GET 為 VIEWER 以上。
  - Given `RbacIT` 的研究清單（現有 approve、return、allowlist、reinit 等）；三種角色與匿名
  - When 對 P1 的 6 個操作各以四種身分呼叫
  - Then `POST route`、`POST scr/{scrNo}/apply`：VIEWER 與 OPERATOR 403 `ACCESS_DENIED`、ADMIN 通過；`POST route/preview`、`POST scr`、`POST decomposition`、`POST decomposition/signoff`：VIEWER 403、OPERATOR 與 ADMIN 通過；`GET route`、`GET scr`、`GET decomposition`：三角色皆通過；匿名一律 401；被拒者迷你 Bridge 請求數 0；清單只增不改（既有項不動）；`RbacIT:452-463` 的研究規則 matcher 清單由恰八條改為恰九條（加 `POST …/scr/*/apply`，保留「夾在 sysadmin 與 settings 規則之間」的次序斷言）；`SecurityConfig`：`route` 的 ADMIN 規則 P0 已預置（`SecurityConfig.java:105`），`scr/*/apply` 為本期新增的一條 ADMIN matcher 且置於通用規則之前（先中者定案），其餘落在通用 OPERATOR 以上規則
  - 判定：gradlew test --tests "com.aisdlc.console.infrastructure.security.RbacIT.AT_961_15_6*"（cwd＝AgentConsole/backend）
- **AT-961-15-7**（JUnit｜`ResearchFlowPolicyTest`｜Unit｜AC-R2P-14-1）ResearchFlowPolicy 的 P1 衍生規則表驅動：route、TCS 相態直接取游標，build 相態依 Console 專案與 FSM 衍生，SCR_OPEN 原樣取用。
  - Given `ResearchFlowPolicy.effective(research, project, latestRun, fsmView)` 與契約 §1.4 API-RP-04 的條件表；游標與 FSM 視圖的組合夾具
  - When 逐列：`flowStep=route`；`flowPhase` 為 `TCS_DRAFTING`、`TCS_PENDING`；`consoleProjectId` 非空、無 run、FSM 為 SPEC_FROZEN 且已 negotiate；SCR 開啟（`flowPhase=SCR_OPEN`）；`furthestStep` 的取較後者
  - Then route 與 TCS 相態：`effective` 等於 DB 游標（含 `flowStatus`）；上述 build 條件回 `build`／`BUILD_READY`；`SCR_OPEN` 原樣取用；`furthestStep` 為游標與 effective 較後者；純函式、無 I/O；`flowStatus` 不自行衍生（沿 D-59(3)）
  - 判定：gradlew test --tests "com.aisdlc.console.domain.service.ResearchFlowPolicyTest.AT_961_15_7*"（cwd＝AgentConsole/backend）
- **AT-961-15-8**（JUnit｜`ResearchBridgeShapeTest`｜Contract｜AC-R2P-19-1、AC-R2P-14-1）源頭鎖：P1 的 Bridge 常數（路由步驟名、路由與 SCR 狀態、reason、事件型別）被 console-api 的契約形狀認得。
  - Given `support/BridgeSource.java`（自 Bridge 原始碼抽鍵集合）；Bridge 的 `app/research/route.py`、`scr.py` 常數；console-api 的 DTO 列舉與 `ErrorReasons`
  - When 抽取 Bridge 常數集合與 console-api 集合比對
  - Then 路由步驟名集合等於 V19 `research_route_steps.step` 的 CHECK 列舉；路由狀態、SCR 狀態、`reason_class`、`source_kind` 各等於 V19 對應 CHECK；Bridge 的 P1 reason 集合等於 `P1_REASONS`；`research.route`、`research.scr` 事件鍵集合等於契約 §3；任一端改名而另一端未改即紅
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchBridgeShapeTest.AT_961_15_8*"（cwd＝AgentConsole/backend）
- **AT-961-15-9**（JUnit｜`ResearchApiIT`｜Integration｜AC-R2P-11-1、AC-R2P-11-4）ResearchProjectDetail 帶唯讀 targetScope（取自 research_projects.target_scope），供預選卡與差異判斷（D-107）。
  - Given DB 夾具：三個專案 `target_scope` 為 `AISDLC_MODULE`、`STANDALONE_PROJECT`、`UNDECIDED`
  - When GET `/api/v1/research/projects/{id}`
  - Then `data.targetScope` 逐值相等；為唯讀欄位（不出現在任何請求 DTO）；P0 既有詳情欄位位元組與順序不變（黃金檔差異只多一鍵）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchApiIT.AT_961_15_9*"（cwd＝AgentConsole/backend）
- **AT-961-15-E-1**（JUnit｜`ResearchRouteApiIT`｜Integration｜AC-R2P-19-1）console-api 透傳 Bridge 的結構化錯誤：狀態碼與 reason 與 details 逐字不變，且 POST 不重試。
  - Given 迷你 Bridge 回放：409 `branch_exists`、422 `target_not_empty`、422 `public_confirmation_required`、409 `route_conflict`、502 `route_step_failed`、409 `scr_open`、409 `scr_limit`
  - When 對應端點各呼叫一次
  - Then 狀態碼、`reason`、`details` 逐字透傳；每個 POST 迷你 Bridge 請求數恰 1（不重試）；錯誤封包形狀為 `{code, message, errors[], reason, details, traceId}`
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchRouteApiIT.AT_961_15_E_1*"（cwd＝AgentConsole/backend）
- **AT-961-15-E-2**（JUnit｜`ResearchApiIT`｜Integration｜AC-R2P-21-2）P0 未結 R-1（D-123 歸 API-P1）：404 文案依 details 或路徑區分，allowlist 條目不存在不再寫成研究專案不存在（reason 仍為 research_not_found）。
  - Given 迷你 Bridge 回放 `PATCH /research/allowlist/{id}` 的 404（`details` 指出 allowlist 條目）；另一組研究專案不存在的 404
  - When PATCH `/api/v1/research/allowlist/{不存在 id}`；GET `/api/v1/research/projects/{不存在 id}`
  - Then 前者 404 `research_not_found` 且 `message` 指出「允許清單條目不存在」；後者訊息仍為「研究專案不存在或已刪除」；兩者 reason 相同、訊息不同；修改只在 console-api 的 `ResearchBridgeErrors.java:50`，Bridge 零改動（`git diff` 為空）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchApiIT.AT_961_15_E_2*"（cwd＝AgentConsole/backend）
- **AT-961-16-4**（JUnit｜`ResearchRouteApiIT`｜Integration｜AC-R2P-04-11、AC-R2P-13-7）console-api 的 CapabilitiesDto：P1 欄位 camelCase 轉出、快取 30 秒、不透出內部路徑以外的環境資訊。
  - Given 迷你 Bridge 回放含 `gh_cli:{ok,authenticated}`（`NOT-EVALUABLE`）、`scaffold_root`、`scaffold_templates[]`、`repo_writable` 的 13 鍵本文
  - When GET `/api/v1/research/capabilities` 兩次（30 秒內）；改迷你 Bridge 回放後再 GET（以假時鐘跨 30 秒）
  - Then 回應 `ghCli.authenticated`（字串 `NOT-EVALUABLE` 原樣）、`scaffoldRoot`、`scaffoldTemplates`、`repoWritable` 對應；30 秒內第二次不打 Bridge（迷你 Bridge 請求數恰 1）、跨 30 秒再打；無 DB 時仍 200 且 `db` 為假（沿 P0）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchRouteApiIT.AT_961_16_4*"（cwd＝AgentConsole/backend）
- **AT-961-20-E-3**（JUnit｜`ResearchApiIT`｜Contract｜AC-R2P-23-1）console-api 對帳 DTO 與 OpenAPI 說明涵蓋第三態：ReconcileResultDto 的 status 說明含 pending_correction，並原樣透傳。
  - Given `ReconcileResultDto.java:29` 的 Schema 說明（現為「ok｜drift｜NOT_EVALUABLE」）；迷你 Bridge 回放含 `pending_correction` 的 `checks[]`
  - When POST `…/reconcile`；讀 `/v3/api-docs` 的 schema 說明
  - Then 回應 `checks[].status` 原樣為 `pending_correction`；OpenAPI 說明列出四個值（`ok`、`drift`、`NOT_EVALUABLE`、`pending_correction`）；契約 API-RP-18 的值域勘誤見 §4.4 E2；既有三值的斷言不變
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchApiIT.AT_961_20_E_3*"（cwd＝AgentConsole/backend）
- **AT-961-21-1**（JUnit｜`ResearchApiIT`｜Integration｜AC-R2P-02-4）records/audit 的 V19 口徑：R7、R8 取自路由與拆解表，missing 恰為尚未交付者。
  - Given DB 夾具：甲專案已分流且拆解簽核；乙專案 Gate 0 後尚未分流；丙專案有 SCR 與自癒步驟；口徑（⚖P1-16）：R7＝`research_route_decisions` 筆數、R8＝`research_decompositions` 筆數、R10＝`v_research_healing_attempts` 筆數、R11＝`research_deliveries` 筆數、R12＝`research_scr` 筆數
  - When GET `…/records/audit`
  - Then 甲：R7、R8 各 ≥1、`missing` 恰含 `R11`（交付屬 P2；R10、R12 允許為 0）；乙：`missing` 含 `R7`、`R8`、`R11`；丙：R10 與 R12 的 `count` 為對應列數；`classes[]` 恰 14 類；P0 的 R1 至 R6、R9、R13、R14 口徑不變
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchApiIT.AT_961_21_1*"（cwd＝AgentConsole/backend）
- **AT-961-21-2**（JUnit｜`ResearchApiIT`｜Integration｜AC-R2P-02-5）audit_log：ADMIN 確認分流、OPERATOR 簽核拆解各有一列 2xx 寫入審計，並與 R7、R8 同 trace_id 含 digest 與理由。
  - Given `AbstractApiIT`；ADMIN 與 OPERATOR 憑證；迷你 Bridge；分流與簽核走完
  - When 查 `console.audit_log`；讀 `research_route_decisions` 與 `research_decompositions` 的對應事件
  - Then 分流確認與簽核各有一列 2xx（欄位含 subject、role、method、path、`trace_id`）；與該請求同 `trace_id` 的 Bridge 事件（`research.route`）payload 含 `published_docs` 摘要與理由（`scope_differs_reason` 若有）；Release Tag 屬 P2（⚖3 的尾巴）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchApiIT.AT_961_21_2*"（cwd＝AgentConsole/backend）
- **AT-961-21-E-1**（JUnit｜`ResearchApiIT`｜Integration｜AC-R2P-02-5）被拒的分流相關寫入請求亦各有一列審計（V6 過濾器對每個 /api 寫入請求恆一列）。
  - Given VIEWER 打 route、OPERATOR 打 route、缺 approver 的簽核、422 的 scr
  - When 各打一次後查 `audit_log`
  - Then 每個被拒請求各一列（401、403、400、422 的狀態碼如實）；`entity_*` 欄取過濾器預設解析（契約不規範）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchApiIT.AT_961_21_E_1*"（cwd＝AgentConsole/backend）
- **AT-961-25-1**（JUnit｜`ResearchFlowPolicyTest`｜Unit｜AC-R2P-14-7）讀端衍生（D-125 之一）：flowPhase 為 TCS_PENDING 且內環 FSM 視圖有 Stage-2 凍結時 effective 回 build／BUILD_READY／IDLE，其餘不變。
  - Given `ResearchFlowPolicy.effective(research, project, latestRun, fsmView)`；`FsmView` 增 `stage2Frozen`（由 `ResearchFsmViewDto` 的 `frozen_stages` 是否含 `Stage-2` 導出）；`ResearchApiIT` 的 fsm 視圖黃金檔
  - When 表驅動：（`TCS_PENDING`，`stage2Frozen` 真）、（`TCS_PENDING`，假）、（`TCS_DRAFTING`，真）、（`ROUTED`，真）、（`TCS_PENDING`，視圖讀不到）；另以 `ResearchApiIT` 讀 `GET …/{id}` 與 `GET …/{id}/fsm`
  - Then 第一列回 `build`／`BUILD_READY`／`IDLE`；其餘各列原樣取 DB 游標（`TCS_DRAFTING` 仍為草擬中）；視圖讀不到時不衍生（沿 P0 的 FSM 讀不到不假設）；`stage2Frozen` 只由 `frozen_stages` 導出，不另存第二份狀態；純函式、無 I/O；`ResearchFlowPolicyTest` 與 `ResearchApiIT` 既有 fsm 視圖斷言只增 `stage2Frozen` 鍵、其餘不改（§4 第 31 列）
  - 判定：gradlew test --tests "com.aisdlc.console.domain.service.ResearchFlowPolicyTest.AT_961_25_1*"（cwd＝AgentConsole/backend）
- **AT-961-25-3**（JUnit｜`ResearchApiIT`｜Integration｜AC-R2P-14-7）凍結後觸發（D-125 之三）：既有 SDD freeze 服務成功後，若專案綁研究專案則呼叫 Bridge :reconcile 恰一次，其他情況不呼叫。
  - Given `AbstractApiIT`；迷你 Bridge（記錄請求）；既有 `POST /api/v1/projects/{id}/sdd/freeze`；三個專案：綁研究專案、未綁、綁研究專案但凍結失敗（422）
  - When 各以 OPERATOR 呼叫 freeze
  - Then 綁研究專案且成功：迷你 Bridge 收到恰一次 `:reconcile`（console-api 不寫任何研究表）；未綁專案：Bridge `:reconcile` 請求 0 次，既有 freeze 行為與回應位元組不變；凍結失敗：不呼叫；對帳呼叫失敗（502）時 freeze 本身仍成功並回應成功（對帳失敗只記日誌，不讓已成功的凍結回錯）；`routers/sdd.py` 零改動（`git diff` 為空）
  - 判定：gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchApiIT.AT_961_25_3*"（cwd＝AgentConsole/backend）

### 3.3 frontend（vitest；徑②）

- **AT-961-16-5**（vitest｜`components/domain/research/RouteDrawer.test.tsx`｜Unit｜AC-R2P-11-6、AC-R2P-04-11、AC-R2P-13-7）前端依 capabilities 缺項停用控件並說明（D-114、IFACE §8.3）：git 缺→預演與確認兩軌皆停用；repoWritable 假→軌道 A 卡；ghCli.ok 假→僅 GitHub 勾選；scaffoldRoot 為 null 或範本空→軌道 B 卡；mock-only→兩軌皆停用。
  - Given `Providers` 與 `stubApi`；capabilities 夾具七組：全可用；`git.ok` 假；`repoWritable` 假；`ghCli.ok` 假；`scaffoldRoot` 為 null；`scaffoldTemplates` 為空；`mode` 為 `mock-only`
  - When 渲染 RouteDrawer（ADMIN）
  - Then 全可用：兩卡與 GitHub 勾選皆可用；`git.ok` 假：預演與確認皆停用並說明「此部署找不到 git，無法分流」；`repoWritable` 假：軌道 A 卡停用並說明「此部署無法寫入 monorepo（容器模式）；請改用本機模式」；`ghCli.ok` 假：僅「建立 GitHub 遠端」勾選停用並說明「找不到 gh；可先建本地專案，之後自行推送」（本地骨架仍可）；`scaffoldRoot` 為 null 或範本為空：軌道 B 卡停用並說明「尚未設定 BRIDGE_SCAFFOLD_ROOT 或無可用範本」；`mock-only`：兩軌皆停用並說明「容器模式只跑 mock claude 的驗收；真分流限本機模式」；非 ADMIN 的確認停用 `title` 為「權限不足」；文案取 `lib/help/research-workspace.ts` 登記值（純文字）；停用的控件 `disabled` 且不送出任何請求
  - 判定：npx vitest run components/domain/research/RouteDrawer.test.tsx -t AT_961_16_5（cwd＝AgentConsole/frontend）
- **AT-961-16-E-2**（vitest｜`components/domain/research/RouteDrawer.test.tsx`｜Unit｜AC-R2P-04-11）capabilities 載入失敗時步驟 3 顯示錯誤態，不假裝可用。
  - Given `stubApi` 讓 capabilities 回 502 與 503
  - When 開啟步驟 3 面板
  - Then 顯示錯誤態與重試鈕（含失敗原因的純文字）；兩卡與確認鈕皆停用；不顯示預設為可用的表單
  - 判定：npx vitest run components/domain/research/RouteDrawer.test.tsx -t AT_961_16_E_2（cwd＝AgentConsole/frontend）
- **AT-961-17-1**（vitest｜`components/domain/research/RouteDrawer.test.tsx`｜Unit｜AC-R2P-11-1）Gate 0 核准後進入第 3 步：抽屜顯示卡 A、卡 B 與評估維度表，依 PRD target_scope 預選其一，再進入可重開。
  - Given `Providers` 與 `stubApi`；研究專案游標在 `route`（Gate 0 已核准）；`targetScope` 分別為 `AISDLC_MODULE`、`STANDALONE_PROJECT`、`UNDECIDED`；capabilities 全可用
  - When 渲染步驟 3 面板（ADMIN）
  - Then 抽屜自動開啟；顯示兩張卡（A 併入 AISDLC、B 獨立專案）與評估維度表：五列（目標場景、路徑規劃、Git 流程、CI/CD 與環境、規格掛載）、三欄（維度、軌道 A、軌道 B）加列頭，內容與來源規格 §4 表一致（文字取 `lib/domain/research.ts` 常數，不內嵌第二份）；預選：`AISDLC_MODULE` 選 A、`STANDALONE_PROJECT` 選 B、`UNDECIDED` 兩卡皆不預選；關閉抽屜後面板提供「重新開啟分流精靈」；所有文字純文字渲染
  - 判定：npx vitest run components/domain/research/RouteDrawer.test.tsx -t AT_961_17_1（cwd＝AgentConsole/frontend）
- **AT-961-17-2**（vitest｜`components/domain/research/RoutePanel.test.tsx`｜Unit｜AC-R2P-11-1）Gate 0 未完成：步驟 3 顯示阻擋頁並連回步驟 2，無任何寫入控件。
  - Given 研究專案游標在 `studio`（外環未凍結）但 `?step=route`（以不經導回的測試入口渲染面板元件）
  - When 渲染 RoutePanel
  - Then 顯示阻擋說明與「回到規格工作室」連結（`?step=studio`）；沒有卡、預演與確認控件；（正常導覽路徑下超前 `?step=` 由工作區導回，見 AT-961-19-1）
  - 判定：npx vitest run components/domain/research/RoutePanel.test.tsx -t AT_961_17_2（cwd＝AgentConsole/frontend）
- **AT-961-17-3**（vitest｜`components/domain/research/RouteDrawer.test.tsx`｜Unit｜AC-R2P-11-4、AC-R2P-12-3）卡 A 欄位：分支名預設 feature/issue-<NNNN>、基底 ref 預設 main、掛載目標下拉取自落點目標清單並附出處。
  - Given `stubApi`：專案 `rpNo` 為 7；capabilities 夾具；落點目標清單取 `lib/domain/research.ts` 的 `PLACEMENT_TARGETS`（四值，每項附出處句；與 Bridge 常數由 AT-961-17-E-2 對拍，D-100）
  - When 選卡 A
  - Then 分支名欄預設 `feature/issue-0007`、基底 ref 預設 `main`；掛載目標為下拉（非自由文字輸入）、選項為四個模組且每項旁顯示出處句；預設選項取 PRD 解析值並標「預設」；改選他項後預演請求帶 `targetModule`；分支名即時驗證（不合 `^feature/[a-z0-9-]{1,40}$` 顯示欄位錯誤並停用預演；常數取 `lib/domain/research.ts`）；模組登錄預覽唯讀顯示
  - 判定：npx vitest run components/domain/research/RouteDrawer.test.tsx -t AT_961_17_3（cwd＝AgentConsole/frontend）
- **AT-961-17-4**（vitest｜`components/domain/research/RouteDrawer.test.tsx`｜Unit｜AC-R2P-13-3、AC-R2P-13-7）卡 B 欄位：專案名稱、owner、庫名、範本下拉取自 capabilities、GitHub 設定預設 Private、Public 需輸入庫名確認並顯示公開警告、CI 與 compose 勾選。
  - Given `stubApi`；capabilities 的 `scaffoldTemplates` 為 `[python-fastapi]`
  - When 選卡 B；填專案名稱、owner、庫名；切 Public；輸入確認名；切換 CI 與 compose 勾選
  - Then 範本為下拉且只列 capabilities 的範本（P1 僅 `python-fastapi`）；Visibility 預設 Private；切到 Public 顯示警告「PRD 與證據矩陣將公開」並出現「重新輸入庫名」欄；確認名與庫名不完全相同（含大小寫、尾端空白）時預演與確認鈕停用，完全相同才啟用；專案名稱、owner、庫名即時驗證（`project_name` 與 `repo_name` 取 `^[a-z][a-z0-9-]{1,38}$`、`owner` 取 `^[A-Za-z0-9][A-Za-z0-9-]{0,38}$`；常數取 `lib/domain/research.ts`）；CI 與 docker compose 為可勾選控件（預設勾選）；送出時 `projectName`、`owner`、`repoName`、`visibility`、`confirmRepoName`、`createGithub`、`ci`、`dockerCompose` 皆正確；請求本文不含 `targetPath`（D-106 退役）
  - 判定：npx vitest run components/domain/research/RouteDrawer.test.tsx -t AT_961_17_4（cwd＝AgentConsole/frontend）
- **AT-961-17-5**（vitest｜`components/domain/research/RouteDrawer.test.tsx`｜Unit｜AC-R2P-11-2）預演面板：OPERATOR 可預演，動作清單以純文字渲染並標示外部系統，預演不改任何狀態。
  - Given `stubApi`：預演回 `actions[]`（含 `external: true` 的 GH_REPO_CREATE 與內含 `<script>` 字串的 target）；OPERATOR 憑證
  - When 按「預演」
  - Then 發出一次 `previewResearchRoute` 請求；渲染動作清單（動作、目標、外部系統徽章）；`<script>` 以純文字顯示（無 `dangerouslySetInnerHTML`）；預演後不發任何 POST route；預演中顯示進行中狀態；預演失敗（422）逐欄顯示違規；「確認執行」在預演通過前停用
  - 判定：npx vitest run components/domain/research/RouteDrawer.test.tsx -t AT_961_17_5（cwd＝AgentConsole/frontend）
- **AT-961-17-6**（vitest｜`components/domain/research/RouteDrawer.test.tsx`｜Unit｜AC-R2P-11-5、AC-R2P-11-6、AC-R2P-11-4）確認僅 ADMIN；差異警示與一句理由必填；VIEWER 全面停用且 title 為權限不足。
  - Given `stubApi`；PRD `targetScope` 為 `AISDLC_MODULE`；VIEWER、OPERATOR、ADMIN 憑證
  - When 各角色渲染；ADMIN 選軌道 B（與 PRD 不同）；理由輸入 0、1、200、201 字元
  - Then VIEWER：所有控件停用、`title` 為「權限不足（唯讀角色）」；OPERATOR：可選卡、填參數、預演，確認鈕停用且 `title` 說明僅 ADMIN；ADMIN：確認鈕在預演通過後啟用；分流與 PRD 不同時顯示差異警示（並列 PRD 範圍與所選軌道）並出現必填理由欄，0 與 201 字元確認鈕停用且有欄位錯誤、1 與 200 字元啟用；確認送出時請求帶 `scopeDiffersReason`；`approver` 不出現在請求本文
  - 判定：npx vitest run components/domain/research/RouteDrawer.test.tsx -t AT_961_17_6（cwd＝AgentConsole/frontend）
- **AT-961-17-7**（vitest｜`components/domain/research/RoutePanel.test.tsx`｜Unit｜AC-R2P-11-3）逐步進度與失敗重試：執行中顯示進度清單，部分失敗顯示失敗步驟與原因並提供重試，完成後唯讀摘要與前往下一步。
  - Given `stubApi` 路由 steps 序列：RUNNING；某步 FAILED（`stderrTail` 含脫敏後原因）；SUCCEEDED（含 `gitBranch`、`repoUrl`、`consoleProjectId`）；SSE 替身推送 `research.route`
  - When 渲染 RoutePanel 三個狀態（ADMIN；另 OPERATOR 看失敗態）
  - Then 執行中：確認為同步請求，未回應前面板顯示進行中並由 SSE 事件逐步更新步驟（步驟名、狀態圖示與文字、耗時；含斷線以 REST `GET …/route` 回補）；失敗：502 `route_step_failed` 後顯示失敗步驟與原因（純文字）與「重試失敗步驟」（僅 ADMIN 可按、送出 `retry: true`；OPERATOR 停用並說明），已成功步驟不顯示重試；完成：唯讀摘要（分支、遠端 URL 純文字加安全連結 `rel="noopener noreferrer"`、Console 專案連結）與「前往拆解與執行」（導向 `?step=build`）；遠端 URL 只在符合 `https://github.com/<owner>/<repo>` 形時才成連結
  - 判定：npx vitest run components/domain/research/RoutePanel.test.tsx -t AT_961_17_7（cwd＝AgentConsole/frontend）
- **AT-961-17-8**（vitest｜`components/domain/research/RoutePanel.test.tsx`｜Unit｜AC-R2P-11-6）部署不支援的錯誤態：預演 422 route_unsupported_in_deployment 時指出缺項，續做時還原已選卡與參數。
  - Given `stubApi`：預演回 422 `route_unsupported_in_deployment`（`details.missing` 為 `["gh", "repo_writable"]`）；另一情境：路由 FAILED 後重新載入頁面
  - When 按預演；重新載入
  - Then 顯示錯誤態並把缺項對映成中文（「gh 命令不可用」「無法寫入程式庫」），不顯示成功態；重新載入後還原已選卡與參數（取自 API 的路由列與 PRD 預設，不取瀏覽器儲存）與已完成步驟，並從失敗步驟續（沿 W-R1：游標取自 API）
  - 判定：npx vitest run components/domain/research/RoutePanel.test.tsx -t AT_961_17_8（cwd＝AgentConsole/frontend）
- **AT-961-17-E-1**（vitest｜`components/domain/research/RouteDrawer.test.tsx`｜Unit｜AC-R2P-13-3）Public 確認的邊界：差一個字元、大小寫不同、尾端空白、貼上不可見字元皆視為不符。
  - Given 卡 B 庫名 `demo-app`、Public
  - When 確認名輸入 `demo-ap`、`Demo-App`、`demo-app `、`demo-app\u200b`、`demo-app`
  - Then 前四者鈕停用、最後一個啟用；比對為完全相等（不修剪、不正規化）
  - 判定：npx vitest run components/domain/research/RouteDrawer.test.tsx -t AT_961_17_E_1（cwd＝AgentConsole/frontend）
- **AT-961-17-E-2**（vitest｜`lib/domain/research.test.ts`｜Unit｜AC-R2P-11-5、AC-R2P-13-3、AC-R2P-11-4）前端分流常數與後端單一來源對拍：分支名與庫名正規式、理由上限、SCR 上限皆與契約字面相等。
  - Given `lib/domain/research.ts` 的 P1 常數；契約 `API_Contract_ResearchToPRD.md` §1.2 的 `route.*` 列（檔案解析，不手抄）
  - When 解析契約表並比對
  - Then `BRANCH_PATTERN`、`REPO_NAME_PATTERN`、`OWNER_PATTERN`、`SCOPE_REASON_MAX`（200）、`REASON_MAX`（500）與契約列逐字相等；`PLACEMENT_TARGETS` 的四個模組值與 Bridge `app/research/route.py` 常數（以原始碼文字解析，不 import）及 V19 CHECK 列舉逐值相等；改一端而未改另一端時本 AT 紅
  - 判定：npx vitest run lib/domain/research.test.ts -t AT_961_17_E_2（cwd＝AgentConsole/frontend）
- **AT-961-18-1**（vitest｜`components/domain/research/BuildFrontPanel.test.tsx`｜Unit｜AC-R2P-14-1、AC-R2P-14-2）拆解面板：空狀態與觸發拆解、草稿樹、覆蓋矩陣與未覆蓋清單。
  - Given `stubApi`：拆解為 null（尚無）、再為 `DRAFTED`（含樹與覆蓋資料：5 個 AC、其中 2 個未覆蓋）；OPERATOR 與 VIEWER
  - When 渲染 BuildFrontPanel；按「觸發拆解」（送 `POST …/decomposition`）
  - Then 空狀態顯示說明與「觸發拆解」（OPERATOR 以上可按；VIEWER 停用並 `title` 為權限不足）；草稿：樹狀顯示 goals／tasks（文字純文字渲染）、覆蓋矩陣（列為 AC、欄為 task、勾選處為涵蓋）、未覆蓋清單逐一列出兩個 AC；`tasksCount` 與樹內 task 數一致；422 結構化錯誤（`violations[].rule` 為 `max_steps`、`cycle`、`empty_prompt`）顯示閘別與說明、不顯示草稿；觸發為同步請求，進行中顯示忙碌狀態（讀逾時 330 秒）
  - 判定：npx vitest run components/domain/research/BuildFrontPanel.test.tsx -t AT_961_18_1（cwd＝AgentConsole/frontend）
- **AT-961-18-2**（vitest｜`components/domain/research/BuildFrontPanel.test.tsx`｜Unit｜AC-R2P-14-2、AC-R2P-14-3）簽核鈕：未覆蓋者清零或各有一句豁免理由前停用，簽核者為目前使用者，理由 500 字界。
  - Given 同 18-1；豁免輸入
  - When 對兩個未覆蓋 AC 輸入豁免理由：0、1、500、501 字元；補到全部有效後按簽核
  - Then 有任一未覆蓋且無有效豁免時簽核鈕停用並列出原因；理由 0 與 501 字元無效（欄位錯誤）、1 與 500 字元有效；全部有效後啟用；按下送出一次 `POST …/decomposition/signoff`（approver 由後端取 JWT subject，前端不送；豁免隨請求同送）；VIEWER 全停用；成功後面板轉為已簽核唯讀態並顯示 `signedOffBy` 與時間
  - 判定：npx vitest run components/domain/research/BuildFrontPanel.test.tsx -t AT_961_18_2（cwd＝AgentConsole/frontend）
- **AT-961-18-3**（vitest｜`components/domain/research/BuildFrontPanel.test.tsx`｜Unit｜AC-R2P-14-5）stale 狀態：PRD 更新後拆解標過期，顯示說明與重新拆解入口，已簽核後唯讀。
  - Given `stubApi`：拆解 `stale` 為真（已簽核版）與 `SIGNED_OFF` 且不 stale 兩種
  - When 渲染
  - Then stale：顯示「PRD 已更新，拆解已過期」與「重新拆解」（OPERATOR 以上）；執行相關連結停用並說明（沿後端 `decomposition_stale`）；非 stale 的已簽核：樹與矩陣唯讀、無簽核鈕
  - 判定：npx vitest run components/domain/research/BuildFrontPanel.test.tsx -t AT_961_18_3（cwd＝AgentConsole/frontend）
- **AT-961-18-4**（vitest｜`components/domain/research/BuildFrontPanel.test.tsx`｜Unit｜AC-R2P-14-7）TCS 草擬面板：內環鍵已採納才可草擬，顯示草擬中、待凍結、已凍結三態與路徑雜湊，凍結連到既有介面。
  - Given `stubApi`：內環鍵未採納；已採納；TCS 草擬中（`flowPhase` 為 `TCS_DRAFTING`）；待凍結（`TCS_PENDING`，`tcsRelPath`、`tcsSha256` 有值）；已凍結
  - When 渲染
  - Then 未採納或尚無拆解列：「草擬測試規格」停用並說明（需先完成分流並觸發拆解，D-110）；齊備：可按（OPERATOR 以上）並送出 `startResearchStage('tcs-draft')`；草擬中顯示進行中；待凍結顯示 TCS 路徑與 sha256 前 12 碼與「前往凍結」連結（導向既有專案凍結介面，路徑取既有路由常數）；`tcs_invalid` 失敗顯示缺項說明（缺的 AC、孤兒 AT；純文字）；已凍結顯示完成；VIEWER 停用
  - 判定：npx vitest run components/domain/research/BuildFrontPanel.test.tsx -t AT_961_18_4（cwd＝AgentConsole/frontend）
- **AT-961-18-5**（vitest｜`components/domain/research/BuildFrontPanel.test.tsx`｜Unit｜AC-R2P-14-3、AC-R2P-14-5）到既有 freeze、import、execute 的連結與執行閘說明：未簽核或未凍結時執行連結停用並說明原因。
  - Given `stubApi`：四種狀態組合（未簽核；已簽核但 TCS 未凍結；皆完成；stale）
  - When 渲染
  - Then 連結目標為既有路由（`/projects/{consoleProjectId}/…`）；只有「已簽核、未 stale、TCS 已凍結、無 SCR 開啟」時執行連結啟用；其餘停用並顯示對應原因（草稿未經人工審批、TCS 尚未凍結、拆解已過期、規格變更中）；看板、自癒與終端屬 P2，本面板不渲染
  - 判定：npx vitest run components/domain/research/BuildFrontPanel.test.tsx -t AT_961_18_5（cwd＝AgentConsole/frontend）
- **AT-961-18-6**（vitest｜`components/domain/research/BuildFrontPanel.test.tsx`｜Unit｜AC-R2P-14-1）SCR 開啟時本面板的操作停用並說明（與後端 409 scr_open 一致）。
  - Given `stubApi`：`flowPhase` 為 `SCR_OPEN`
  - When 渲染
  - Then 顯示「規格變更中」橫幅；觸發拆解、簽核、草擬測試規格皆停用並說明；發起 SCR 的按鈕屬 P2、不在本面板（⚖P1-17）
  - 判定：npx vitest run components/domain/research/BuildFrontPanel.test.tsx -t AT_961_18_6（cwd＝AgentConsole/frontend）
- **AT-961-18-7**（vitest｜`components/domain/research/BuildFrontPanel.test.tsx`｜Unit｜AC-R2P-14-1）Bridge 或 API 不可用時顯示錯誤態與快取，不顯示空白。
  - Given `stubApi` 讓拆解與 FSM 視圖請求失敗（502、504）
  - When 渲染
  - Then 顯示錯誤態與重試；先前成功的資料（若有）以「資料可能過期」標示保留；VIEWER 唯讀
  - 判定：npx vitest run components/domain/research/BuildFrontPanel.test.tsx -t AT_961_18_7（cwd＝AgentConsole/frontend）
- **AT-961-18-E-1**（vitest｜`components/domain/research/BuildFrontPanel.test.tsx`｜Unit｜AC-R2P-14-2）覆蓋矩陣在大型 PRD 下仍可渲染：200 個 AC 乘 24 個 task 不阻塞互動。
  - Given 夾具：200 個 AC、24 個 task
  - When 渲染並切換顯示未覆蓋篩選
  - Then 渲染完成且互動回應（以假計時器量測篩選切換不超過 200 毫秒；量測值寫入證據，未校準）；列與欄皆有可及名稱
  - 判定：npx vitest run components/domain/research/BuildFrontPanel.test.tsx -t AT_961_18_E_1（cwd＝AgentConsole/frontend）
- **AT-961-19-1**（vitest｜`components/domain/research/ResearchWorkspaceView.test.tsx`｜Unit｜AC-R2P-21-5）?step=route 與 ?step=build 不再是占位，?step=deliver 仍為占位；Gate 0 未完成時超前導回。
  - Given `Providers` 與 `stubApi`；游標在 route（Gate 0 已核准、最遠到第 5 步）；游標在 studio（外環未凍結）
  - When 開啟 `?step=route`、`?step=build`、`?step=deliver`；游標在 studio 時開啟 `?step=route`
  - Then route 顯示 RoutePanel、build 顯示 BuildFrontPanel（不顯示 `research-placeholder`）；deliver 仍顯示占位面板（「本步驟於後續階段提供」、唯讀、無寫入控件、回到游標所在步連結）；游標在 studio 時 `?step=route` 導回 studio（超前不可達）；既有 P0 的占位測試 `AT_960_19_5` 僅 deliver 一個參數（§4 第 12 列只改預期值）
  - 判定：npx vitest run components/domain/research/ResearchWorkspaceView.test.tsx -t AT_961_19_1（cwd＝AgentConsole/frontend）
- **AT-961-19-2**（vitest｜`lib/help/research-workspace.test.ts`｜Unit｜AC-R2P-21-2）說明三道鎖與寫實內容：research-workspace 的第 3、4 步說明寫實，三道鎖綠，計數不變。
  - Given `lib/help/research-workspace.ts`（`steps` 欄）、`lib/help/registry.ts`、`lib/help/lint.ts`；既有 `registry.test.ts`、`content.test.ts`
  - When 解析並跑既有三道鎖
  - Then 第 3 步說明含：分流兩軌的差異、OPERATOR 可預演、僅 ADMIN 可確認、預演零副作用、軌道 B 的 token 不落地；第 4 步說明含：拆解、覆蓋與豁免、簽核、TCS 草擬與凍結走既有介面、看板屬後續；兩段文字過 `lint.ts`（無禁字、無過長句）；`HELP_PAGES` 為 22 項、`HELP_ROUTES` 為 25 條、`StateTableId` 為 19 張（P1 不變）；`PENDING_HELP_PAGES` 仍為空；既有 `registry.test.ts`、`content.test.ts` 零改動仍綠
  - 判定：npx vitest run lib/help/research-workspace.test.ts lib/help/registry.test.ts lib/help/content.test.ts（不帶 -t；`lib/help/research-workspace.test.ts` 為 PKG-FE-D1 新增檔，其餘為既有檔零改動；cwd＝AgentConsole/frontend）
- **AT-961-19-3**（vitest｜`components/domain/help/stateKeys.test.ts`｜Unit｜AC-R2P-21-2）researchFlow 狀態表詞彙涵蓋 P1 相態並與 FLOW_PHASE_LABEL 的鍵一致。
  - Given `lib/help/states.ts` 的 `researchFlow` 表、`lib/domain/research.ts` 的 `FLOW_STATUS_LABEL`、`FLOW_PHASE_LABEL`（含 `ROUTING`、`ROUTED`、`TCS_DRAFTING`、`TCS_PENDING`、`SCR_OPEN`）
  - When 跑既有 `stateKeys.test.ts` 的 `researchFlow` 上游對拍
  - Then 狀態表每個詞條有說明文字、鍵集合等於上游常數鍵集合（單向取上游，不經 `STATE_SOURCES`）；P1 相態各有寫實說明；測試檔零改動仍綠
  - 判定：npx vitest run components/domain/help/stateKeys.test.ts（不帶 -t：既有檔零改動、內無標題含 AT 字樣，帶 -t 會把全部測試篩掉而假綠；cwd＝AgentConsole/frontend）
- **AT-961-19-4**（vitest｜`components/domain/research/FlowStepper.test.tsx`｜Unit｜AC-R2P-21-5）FlowStepper 的 route 與 build 步驟狀態：進行中、失敗阻擋、SCR 進行中標示。
  - Given 游標與 effective 組合：route／ROUTING（RUNNING）、route 失敗（FAILED）、route／ROUTED 完成、`SCR_OPEN`
  - When 渲染 FlowStepper
  - Then route 進行中為 CURRENT、失敗為 BLOCKED 且顯示 `blockedReason`（取 `flow_detail` 的純文字）、完成為 DONE 且 build 為 CURRENT；`SCR_OPEN` 時顯示「SCR 進行中」標示；步驟按鈕的可及名稱含狀態；既有 P0 案例零改動仍綠
  - 判定：npx vitest run components/domain/research/FlowStepper.test.tsx -t AT_961_19_4（cwd＝AgentConsole/frontend）
- **AT-961-19-5**（vitest｜`lib/api/endpoints.test.ts`｜Contract｜AC-R2P-21-5）端點函式與型別：新增 9 個函式（總數 118），operationId 與契約一一對應，schema.d.ts 重產含之，型別與契約 DTO 逐欄相符。
  - Given `lib/api/endpoints.ts`、`lib/api/types.ts`、`lib/api/schema.d.ts`（由 backend OpenAPI 重產）、`lib/api/endpoints.test.ts` 的 `EXPECTED`（現總數 109）與元鎖 `si.endpoints.test.ts:46`
  - When 跑 `endpoints.test.ts` 與 `si.endpoints.test.ts`；比對 schema.d.ts 的 operationId
  - Then 函式總數 118（現 109，`endpoints.test.ts:288`；與 AT-961-15-3 的新增操作數 9 同源）；新增 `previewResearchRoute`、`routeResearchProject`、`getResearchRoute`、`openResearchScr`、`listResearchScr`、`applyResearchScr`、`getResearchDecomposition`、`triggerResearchDecomposition`、`signoffResearchDecomposition`（九個 operationId 為 D-118 定案）；`EXPECTED` 逐一加入；`si.endpoints.test.ts:46` 的釘值字串同批改為 118（兩檔同包同改，只改一邊必紅）；`schema.d.ts` 含 9 個 operationId 且重產後無差異（FE-W 單棒，API-P1 合併後）；`RouteDecisionDto`、`RouteStepDto`、`ScrDto`、`DecompositionDto` 與契約 §1.3（含勘誤）逐欄相符（欄位名與可空性）；`endpoints.test.ts` 內該 `it` 的標題加 `AT_961_19_5` 字樣（只改標題；`-t` 才篩得到）；`reasons.test.ts` 零改動仍綠（研究 reason 只進 `RESEARCH_REASONS`）
  - 判定：npx vitest run lib/api/endpoints.test.ts -t AT_961_19_5（cwd＝AgentConsole/frontend）
- **AT-961-19-6**（vitest｜`tests/design-rules.test.ts`｜Unit｜AC-R2P-21-5）前端靜態鎖遵守：新元件無陰影與漸層、只用設計 token、無手寫 svg、無 emoji、無 outline-none、無 dark:，四區塊名不出現在 app/research。
  - Given 新增與增修的 `components/domain/research/{RouteDrawer,RoutePanel,BuildFrontPanel}.tsx`、`lib/domain/research.ts`、`lib/api/{endpoints,queries,types}.ts`；既有 `design-rules.test.ts`、`layout.test.tsx`、`si.static.test.ts`、`sysadminBackup.test.ts`
  - When 跑既有四個靜態鎖檔
  - Then 皆零改動仍綠；警示標示一律 Lucide 圖示；`queries.ts` 只增不動既有兩行輪詢常數；無 Bridge 埠號字面與 `BRIDGE` 環境變數讀取
  - 判定：npx vitest run tests/design-rules.test.ts components/layout/layout.test.tsx components/domain/si/si.static.test.ts lib/domain/sysadminBackup.test.ts（不帶 -t，理由同 19-3；cwd＝AgentConsole/frontend）
- **AT-961-19-E-1**（vitest｜`lib/domain/research.test.ts`｜Unit｜AC-R2P-21-2）P1 reason 的前端文案表：每個 P1 reason 有中文說明，且不直出伺服器訊息。
  - Given `RESEARCH_REASONS` 與 reason 文案表（`lib/domain/research.ts`）
  - When 對 P1 的 9 個 reason 與 R-2 的 4 個 reason 逐一取文案
  - Then 每個皆有非空中文文案；502 `route_step_failed` 的文案帶失敗步驟名（取 `details.failureStep` 對映 `ROUTE_STEP_LABEL`）；`not_implemented` 保留通用文案（D-111：P1 起無觸發者，保留供 P2 骨架）；`BUILD_READY`「可開始建置」、`PAUSED`「已暫停」、`SCR_OPEN`「SCR 進行中」三個衍生相態標籤已入 `FLOW_PHASE_LABEL`（D-114）
  - 判定：npx vitest run lib/domain/research.test.ts -t AT_961_19_E_1（cwd＝AgentConsole/frontend）
- **AT-961-20-E-2**（vitest｜`lib/domain/research.test.ts`｜Unit｜AC-R2P-23-1）前端對 pending_correction 的判讀（純函式）：第三態不算漂移，仍可被辨識為待校正。
  - Given `lib/domain/research.ts` 對帳結果的判讀函式（現只認 `drift`，`:525-534`）；夾具：`fsm_flow_mapping` 為 `pending_correction`、為 `drift`、為 `NOT_EVALUABLE`
  - When 對三種夾具跑對帳判讀函式（不渲染）
  - Then `pending_correction` 不計入漂移（判讀函式的 `hasDrift` 為假、`pendingCorrection` 為真）；`drift` 照舊為漂移；`NOT_EVALUABLE` 照舊（沿 P0）；`research.ts` 現只認 `drift` 的行為對既有兩值不變
  - 判定：npx vitest run lib/domain/research.test.ts -t AT_961_20_E_2（cwd＝AgentConsole/frontend）
- **AT-961-20-E-4**（vitest｜`components/domain/research/BuildFrontPanel.test.tsx`｜Unit｜AC-R2P-23-1）步驟 4 面板渲染對帳結果：pending_correction 顯示「待校正」說明、不顯示漂移警示橫幅，並提供「重新對帳」入口（元件載具，承接 AT-961-20-E-2 的判讀）。
  - Given `stubApi`：`reconcile` 回 `fsm_flow_mapping` 為 `pending_correction`、`drift`、`NOT_EVALUABLE` 三種夾具；OPERATOR
  - When 渲染 BuildFrontPanel 並載入對帳結果
  - Then `pending_correction`：顯示「待校正」純文字說明與「重新對帳」鈕，無漂移警示橫幅；`drift`：顯示漂移警示橫幅（沿 P0 文案）；`NOT_EVALUABLE`：沿 P0 顯示；載具檔屬 PKG-FE-D2 的允許集合（§5.7）
  - 判定：npx vitest run components/domain/research/BuildFrontPanel.test.tsx -t AT_961_20_E_4（cwd＝AgentConsole/frontend）
- **AT-961-25-4**（vitest｜`components/domain/research/BuildFrontPanel.test.tsx`｜Unit｜AC-R2P-14-7）步驟 4 面板的「重新對帳」：OPERATOR 以上可按、送出一次 reconcile，成功後面板依回應刷新（BUILD_READY）。
  - Given `stubApi`：游標 `build`／`TCS_PENDING` 且 `stage2Frozen` 為真；VIEWER 與 OPERATOR
  - When 渲染 BuildFrontPanel；按「重新對帳」
  - Then VIEWER 停用且 `title` 為權限不足；OPERATOR 可按並送出一次 `POST …/reconcile`；回應後重抓專案詳情，顯示「可開始建置」（`BUILD_READY` 標籤，D-114）；請求失敗顯示錯誤文字並可重試；不呼叫任何其他寫入端點
  - 判定：npx vitest run components/domain/research/BuildFrontPanel.test.tsx -t AT_961_25_4（cwd＝AgentConsole/frontend）

### 3.4 E2E 與指令核對（Docker 全棧、Playwright、git 與靜態工具；主控或整合棒跑）

- **AT-961-22-5**（Playwright｜`tests/e2e/research-p1-docker.stack.spec.ts`｜E2E｜AC-R2P-21-5、AC-R2P-11-6）Docker 全棧（mock-only）：API 直呼預演回缺項，capabilities 如實，UI 停用兩卡並說明。
  - Given Docker 全棧（`docker compose --profile db --profile app --profile full up -d --build`；nginx 80 埠；`E2E_ROOT` 短路徑；只跑 mock claude）；ADMIN、OPERATOR、VIEWER 憑證；以 mock 劇本 `pass` 走到 Gate 0 核准的專案
  - When 以 API 直呼 `GET /api/v1/research/capabilities` 與 `POST …/route/preview`（軌道 A、B）；以 UI 開啟 `?step=route`
  - Then capabilities 的 `ghCli.ok` 為假、`repoWritable` 為假、`scaffoldRoot` 為 null；預演回 422 `route_unsupported_in_deployment` 且 `details.missing` 列出缺項（出口 (k)）；UI 的 RouteDrawer 兩卡停用並顯示「容器模式只跑 mock claude 的驗收；真研究與分流限本機模式」；VIEWER 全停用、OPERATOR 不能確認；零副作用（容器內 repo 與 DB 路由表列數不變）
  - 判定：npx playwright test tests/e2e/research-p1-docker.stack.spec.ts -g AT_961_22_5 --output=<各自目錄>（cwd＝AgentConsole/frontend；Docker 全棧用 tests/e2e/docker.config.ts）
- **AT-961-22-6**（Playwright｜`tests/e2e/research-p1-docker.stack.spec.ts`｜E2E｜AC-R2P-21-5）Docker 全棧：步驟 4 前半與步驟 5 的呈現——build 顯示拆解面板空狀態與停用的草擬，deliver 仍為占位。
  - Given 同 22-5；專案 Gate 0 後尚未分流
  - When 開啟 `?step=build`、`?step=deliver`
  - Then build：顯示 BuildFrontPanel 的空狀態；「草擬測試規格」停用並說明需先完成分流；deliver：占位面板（「本步驟於後續階段提供」）；`?step=build` 在游標為 route 時依既有導回規則可達性與契約一致（沿 AT-961-19-1）；無任何寫入控件可造成副作用
  - 判定：npx playwright test tests/e2e/research-p1-docker.stack.spec.ts -g AT_961_22_6 --output=<各自目錄>（cwd＝AgentConsole/frontend；Docker 全棧用 tests/e2e/docker.config.ts）
- **AT-961-22-7**（Playwright｜`tests/e2e/a11y.mock.spec.ts`｜E2E｜AC-R2P-21-5）a11y 與版面：RouteDrawer 與 BuildFrontPanel 在 1440、1000、600 寬度無水平溢出且 axe 無 serious 與 critical，抽屜焦點陷阱與歸還正確。
  - Given mock spec（`mockApi.ts` 體例）；capabilities 全可用情境；拆解草稿情境（含覆蓋矩陣）
  - When 三種寬度各開 RouteDrawer 與 BuildFrontPanel；以鍵盤開關抽屜
  - Then `scrollWidth` 不大於 `clientWidth`；axe 掃描無 serious、critical（以 `--output` 各自目錄；結果入證據）；抽屜開啟時焦點在抽屜內循環、Esc 關閉後焦點回到觸發鈕；覆蓋矩陣有可及的列與欄名稱
  - 判定：npx playwright test tests/e2e/a11y.mock.spec.ts -g AT_961_22_7 --output=<各自目錄>（cwd＝AgentConsole/frontend；Docker 全棧用 tests/e2e/docker.config.ts）
- **AT-961-22-8**（Playwright｜`tests/e2e/research-p1-docker.stack.spec.ts`｜E2E｜AC-R2P-21-5）P0 既有 E2E 不退步：兩條 Docker 路徑仍綠，唯一改動為占位斷言的預期值。
  - Given 既有 `research-docker.stack.spec.ts`（P0）與 `README.md` 的 AT_960_22_5 敘述（§4 第 13 列）
  - When 跑 P0 全檔（`-g AT_960_22`）
  - Then 兩條路徑（三輪失敗進 ESCALATED、通過後核准凍結）與 SSE 斷線重播仍綠；AT_960_22_5 中「步驟 3～5 占位」改為「步驟 5 占位、步驟 3 與 4 為真面板」，其餘斷言零改動；本檔 P1 新增案例放在新檔 `research-p1-docker.stack.spec.ts`，不改 P0 檔的 helper 以外內容
  - 判定：npx playwright test tests/e2e/research-docker.stack.spec.ts -g AT_960_22 --output=<各自目錄>（cwd＝AgentConsole/frontend；Docker 全棧用 tests/e2e/docker.config.ts）
- **AT-961-23-1**（指令核對｜指令｜Gate｜AC-R2P-02-7）允許變更檔案集合與禁區：只動各包 §5.7 的集合，禁區零差異。
  - Given 本鍵開工基準 commit（RTM-P1 檔頭記錄）與 HEAD；§5.7 的各包集合
  - When `git diff --name-only <基準>..HEAD`（含工作樹未提交：`git status --porcelain`）逐檔歸屬各包集合
  - Then 每個變更檔都屬於某一包集合（或屬主控收尾單窗的根層連動清單）；禁區（根 `CLAUDE.md`、`.claude/`、`tools/`、`AISDLC_SDD/`、`AutoClaude/`、`.github/`〔除 `agentconsole-ci.yml` 的 `paths` 由主控改〕、`docs/01_requirements/ResearchToPRD_PRD.md`、ADR 檔）零差異；§4 各列只改預期值、零刪斷言（以 `git diff` 的刪除行掃描 `expect(`、`assert`、`it(`、`@Test`；例外列依 §4 明示的第 1、5、6、7 列）
  - 判定：git diff --name-only <基準>..HEAD；git diff -U0 <基準>..HEAD -- <§4 列出的測試檔> 掃刪除行（cwd＝monorepo 根；PowerShell 與 bash 皆可）
- **AT-961-23-2**（指令核對｜指令｜Gate｜AC-R2P-02-7）不新增 os.replace、rename、move 站點：研究套件的目錄項原語站點數不增，根層 dirent 鎖綠。
  - Given 基準與 HEAD 的 `app/research/**`；`tools/tests/test_platform_neutral_paths.py`
  - When `git grep -nE "os\.(replace|rename)|shutil\.move|\.rename\(|\.replace\(" -- AgentConsole/engine-bridge/app`（字串 `.replace(` 的 `str.replace` 以人讀排除，記入證據）；跑根層 `TestDirEntryPrimitivesAreAccountedFor`
  - Then 目錄項原語站點相對基準淨增 0；`TestDirEntryPrimitivesAreAccountedFor` rc 0；原子寫檔一律 `fsutil.write_text_atomic`；軌道 B 的複製為「複製→逐檔驗證→原地保留」，不出現改名或搬移
  - 判定：git grep -nE ... ；python -m unittest test_platform_neutral_paths.TestDirEntryPrimitivesAreAccountedFor -v（cwd＝tools/tests；PowerShell 不用裸 cd、rc 先存變數）
- **AT-961-23-3**（指令核對｜指令｜Gate｜AC-R2P-02-7）不新增 hook、守衛碼與根層 tools 模組。
  - Given 基準與 HEAD
  - When `git diff --name-only <基準>..HEAD -- .claude tools .github AISDLC_SDD AutoClaude CLAUDE.md`
  - Then 輸出為空（`.github/workflows/agentconsole-ci.yml` 的 `paths` 由主控收尾單窗另列於證據，不屬開發棒）；`AgentConsole/engine-bridge/app/research/` 之外不新增 `subprocess` 使用者
  - 判定：git diff --name-only <基準>..HEAD -- .claude tools .github AISDLC_SDD AutoClaude CLAUDE.md（cwd＝monorepo 根）
- **AT-961-23-4**（指令核對｜指令｜Gate｜AC-R2P-02-7）新 Python 衛生：encoding 宣告、時間戳帶時區、平台專屬 API 罩 sys.platform、ruff 兩視角 0 錯、LF。
  - Given 本鍵新增與修改的 `AgentConsole/engine-bridge/**/*.py`
  - When `ruff check`（本目錄與 monorepo 根視角各一次）；對新檔掃描 `open(`、`read_text(`、`write_text(` 缺 `encoding`；`datetime.now()` 與 `utcnow()`；`\r` 位元組
  - Then ruff 兩次 rc 0；掃描皆零命中（`datetime.now(timezone.utc)` 形態通過）；所有新文字檔 LF（`.ps1` 例外為 CRLF）
  - 判定：ruff check（cwd＝AgentConsole/engine-bridge）；ruff check AgentConsole/engine-bridge（cwd＝monorepo 根）；自檢腳本的掃描段
- **AT-961-24-1**（指令核對｜指令｜Gate｜AC-R2P-21-6）文件閘與追溯：新文件無測試摘要字樣加四位數字同行、RTM 每列回填、編號不撞號、Architecture 5.4 檢查表逐項有交付。
  - Given 本檔、RTM-P1、SCG-4 報告與各勘誤表；Architecture §5.4 檢查表
  - When 對新文件跑 pre-commit 的測試摘要字樣掃描；RTM 列數與狀態統計；F-907、US-923 至 US-925、AC-961、AT-961 的撞號掃描（`AgentConsole/docs`、`docs`、`AgentConsole` 排除 node_modules）；人讀對照 Architecture §5.4
  - Then 掃描零命中；RTM-P1 列數為 F 1、US 3、AC 25、AT 210，合計 239（1＋3＋25＋210）；TCS §1.1 的 AC 定義列恰 25、§3 的 AT 定義列恰 210；每列四格回填（不得刪列、改號、合併，鐵律 12）；撞號掃描除本鍵文件外零命中；Architecture §5.4 的每一項（路由頁只殼、領域元件、API 條目、純函式與測試、登記表一列、說明登記表、RTM 子表、Architecture 同步、CI paths、契約）P1 皆有對應交付或明示不適用（V-C1）
  - 判定（入庫可跑；各行為獨立指令，行尾井字為期望值）：
    PowerShell（cwd＝monorepo 根；讀值先存變數）：
    $tcs = 'AgentConsole/docs/03_testing/contracts/TCS-ResearchToPRD-P1-20261107.md'; $rtm = 'AgentConsole/docs/06_quality/RTM-ResearchToPRD-P1-20261107.md'
    (Select-String -Path $tcs -Pattern '^- \*\*AC-961-[0-9]+\*\*').Count   # 期望 25
    (Select-String -Path $tcs -Pattern '^- \*\*AT-961-[0-9A-Za-z-]+\*\*').Count   # 期望 210
    (Select-String -Path $rtm -Pattern '^\| `(F|US|AC|AT)-').Count   # 期望 239
    (Select-String -Path $tcs,$rtm -Pattern 'passed|skipped' | Where-Object { $_.Line -match '[0-9]{4,}' }).Count   # 期望 0
    bash（同一 cwd）：
    tcs=AgentConsole/docs/03_testing/contracts/TCS-ResearchToPRD-P1-20261107.md; rtm=AgentConsole/docs/06_quality/RTM-ResearchToPRD-P1-20261107.md
    grep -cE '^- \*\*AC-961-[0-9]+\*\*' "$tcs"   # 期望 25
    grep -cE '^- \*\*AT-961-[0-9A-Za-z-]+\*\*' "$tcs"   # 期望 210
    grep -cE '^\| `(F|US|AC|AT)-' "$rtm"   # 期望 239
    grep -hiE 'passed|skipped' "$tcs" "$rtm" | grep -cE '[0-9]{4,}'   # 期望 0

## 4. 需同步的既有測試與凍結文件勘誤（只改預期值，不刪斷言，例外見共同規則；每筆寫明「為何現值變了」）

> 座標為 SD 寫稿時（HEAD 為 `9c628f0f`）以 Grep 現查的快照（逐字結果見自查檔 `HARDPIN_SCAN.txt`），重跑法＝照座標讀檔；開發棒動手前先對該檔現查行號。**共同規則（AT-961-23-1 的 GATE 核對）**：下列每個 hunk 只動預期值、清單、探針列、快照列或註解；被刪的 `expect`、`it`、`assert`、`@Test` 行為 0；AT 標題與 id 不變。**例外（不只改預期值；各列自寫 hunk 範圍與理由，GATE 核對時逐列放行）**：第 2 列（`BackupJobMigrationIT` 的欄位查詢條件）、第 34 列（`ResearchSchemaMigrationIT` 三處既有斷言）、第 8 列（`test_research_capability.py` 的禁令改寫為只准 `gitops`）、第 9 列（`create_key` 呼叫者集合）、第 13 列（占位面板斷言改為 deliver 一個參數）。product 檔（非測試）隨所屬包交付，列在此處是因為它們與測試同步。

### 4.1 backend 既有測試與 product 連動（PKG-DB-P1、PKG-API-P1）

| # | 檔:行 | 現值 | 改後值 | 為何現值變了 |
|---|-------|------|--------|--------------|
| 1 | 六處 Flyway 版本清單：`AgentConsole/backend/src/test/java/com/aisdlc/console/infrastructure/persistence/SchemaMigrationIT.java:68-69`、`V5UpgradeMigrationIT.java:135-136`、`IssuePriorityMigrationIT.java:130-131`、`BackupJobMigrationIT.java:167-168`、`SiConsoleWritesMigrationIT.java:128-129`、`ResearchSchemaMigrationIT.java:490,493`；`engine-bridge/tests/research_pg_support.py:4,50-59`（`LAST_VERSION` 與檔頭敘述「V1～V18」） | 皆 `containsExactly("1", … "18")`；`ResearchSchemaMigrationIT:493` 另有 `containsEntry("18", "research prd review gate")`；Bridge 夾具套到 V18 | 皆加 `"19"`（`ResearchSchemaMigrationIT` 另加 `containsEntry("19", "research route scr delivery")`）；`research_pg_support.py` 的 `LAST_VERSION` 改 19（`migration_files()` 依數值序讀真檔，不另抄 DDL） | V19 落地（AT-961-1-1、1-E-2）；P0 TCS §4 第 13 列只列五處，`ResearchSchemaMigrationIT` 的自身清單與 Bridge 夾具是 P1 補列 |
| 2 | `AgentConsole/backend/src/test/java/com/aisdlc/console/infrastructure/persistence/BackupJobMigrationIT.java:82-90`（`snapshotOfExistingTables` 的欄位查詢：`information_schema.columns where table_schema = 'console' and table_name <> 'backup_jobs' and table_name not like 'research\\_%'`）；呼叫點 `:97`、`:102`、`:106`、`:154` | 欄位查詢排除 `backup_jobs` 與 `research_` 起頭之表；約束查詢排除 `console.research_` 起頭 | 欄位查詢再加 `and table_name not like 'v\\_research\\_%'`（視圖 `v_research_healing_attempts` 不以 `research_` 起頭，而 `information_schema.columns` 把視圖欄位也列入）；約束查詢**不改**（V19 五表的約束已被既有條件排除，視圖沒有約束）；呼叫點與 `isEqualTo(before)` 不動 | V19 的視圖使「既有表零變動」的比較多出 10 欄而紅（AT-961-1-E-2；P0 TCS §4 第 13 列已預告）；這是查詢條件的改動、不只是預期值 |
| 3 | `AgentConsole/backend/src/test/java/com/aisdlc/console/infrastructure/config/OpenApiIT.java:45`（`EXPECTED`）、`:163`（`EXPECTED_PATH_COUNT`＝101）、`:164`（`EXPECTED_OPERATION_COUNT`＝115）、`:944`（研究路徑 24）、`:953`（`RESEARCH_OPERATION_IDS` 25）、`:972`（`RESEARCH_STATUS_CODES` 26）、以路徑為鍵的回應碼表 | 101／115；研究 24／25／26 | `EXPECTED` 加六條路徑（`…/route/preview`、`…/route`、`…/scr`、`…/scr/{scrNo}/apply`、`…/decomposition`、`…/decomposition/signoff`）；路徑 107、操作 124；研究路徑 30、operationId 34、回應碼表 35；為每個新操作補列。**自算法**：新增路徑＝六條（同路徑 GET 與 POST 合併計一），新增操作＝preview、route、getRoute、openScr、listScr、applyScr、getDecomposition、triggerDecomposition、signoffDecomposition 九個；IFACE 第二版的 107／124 為推論，**以實際新增數為準**並於證據註明算法與差異 | 新增端點；`OpenApiIT` 計數屬共享單點，只給 PKG-API-P1 單棒（AT-961-15-3） |
| 4 | `AgentConsole/backend/src/test/java/com/aisdlc/console/adapter/in/web/ResearchReasonsTest.java:43-46`（`P0_REASONS` 22 個）、`:111-118`（`hasSize(22)` 與後端、前端等號）、`:120-131`（契約與 Architecture 表）、`:134-140`、`:164-170` | 22 個 reason 的四處等號 | `P0_REASONS` 保留，另加 `P0_TAIL_REASONS`（`compile_failed`、`sdd_cli_failed`、`fsm_state_unreadable`、`invalid_request`；R-2，⚖P1-25）與 `P1_REASONS`（9 個）；等號改為三集合聯集（35）；Architecture 表的狀態碼斷言補 P1 與尾巴各項；`reasons.ts` 不污染斷言涵蓋新 reason | +13 個 reason（AT-961-15-4）；測試名單改動與後端常數同在 PKG-API-P1（前端 `reasons.ts` 由 FE-D1 先加，波 1 結束時該 JUnit 暫時紅，主控波 2 收卷後才驗；PACKAGES 第二版 §3） |
| 5 | `AgentConsole/backend/src/test/java/com/aisdlc/console/infrastructure/security/RbacIT.java:342-345`（ADMIN 專屬寫入清單）、`:374-379`（一般寫入清單）、`:404`（GET 清單）、`:452-463`（研究規則 matcher 清單，`containsExactly` 恰八條）、`:486-495`（`route/preview` 探針） | 清單不含 P1 端點 | 只增：`POST route`、`POST scr/{scrNo}/apply` 入 ADMIN 清單；`POST route/preview`、`POST scr`、`POST decomposition`、`POST decomposition/signoff` 入一般寫入清單；三個 GET 入 GET 清單；不改既有項；`:452-463` 的 matcher 清單由八條改九條（加 `POST …/scr/*/apply`，保留次序斷言） | AT-961-15-6（F-03） |
| 6 | product：`AgentConsole/backend/src/main/java/com/aisdlc/console/infrastructure/config/SecurityConfig.java:103-110` | `route` ADMIN 規則於 `:105` 已預置；無 `scr/*/apply` 規則 | 於 `:110` 與通用規則（`:111-112`）之間新增一條 `POST /api/v1/research/projects/*/scr/*/apply` ADMIN；`route` 規則不動 | 先中者定案（AT-961-15-6） |
| 7 | product：`AgentConsole/backend/src/main/java/com/aisdlc/console/domain/exception/ErrorReasons.java:168-232`、`ResearchErrorDocs.java`、`ResearchController.java:224-226`、`ErrorReasons.java:219`（「tcs-draft 屬 P1、尚未實作」敘述） | 無 P1 reason；`tcs-draft` 文字寫尚未實作 | 加 9 個 `RESEARCH_` 前綴常數（與 R-2 尾巴 4 個）；OpenAPI 說明補列；`tcs-draft` 文字訂正為「P1 起可用；`not_implemented` 保留供 P2 骨架」 | AT-961-15-3、15-4；前綴一律 `RESEARCH_`，否則 `IssueReasonsContractTest`、`BackupReasonsContractTest` 的集合鎖紅 |
| 8 | product：`ResearchProjectDetail` DTO 與 `ResearchApiIT` 逐欄斷言（現查） | 無 `targetScope` | 加唯讀 `targetScope`（D-107） | AT-961-15-9 |
| 9 | product：設定鍵目錄與設定 API 測試（現查；`CONFIG_KEY_UNKNOWN`＝`ErrorReasons.java:59`）、`RequestFactoryProvider` 與逾時表測試（現查） | 無 `research.github_token`；研究寫入讀逾時 30 秒 | 加加密鍵 `research.github_token`（預設空）；`route` 與 `decomposition` 讀逾時 330 秒 | D-98、D-105（AT-961-14-6、14-8） |
| 10 | product：既有 execute／resume 啟動服務與其 IT（類別現查；`UNSIGNED_DRAFT`＝`ErrorReasons.java:63` 的既有斷言不得變） | 無研究專案前置守衛 | 加單一前置守衛（僅 `research_projects.console_project_id` 命中時生效；檢查序 `scr_open`、`decomposition_stale`、`fsm_state_conflict`）；既有斷言零改動；新增非研究專案回歸 AT | D-102（AT-961-11-3～11-6、11-E-2） |
| 11 | `AgentConsole/backend/src/test/java/com/aisdlc/console/adapter/in/web/ResearchEndpointsIT.java:524-526`（迷你 Bridge 回放 `tcs-draft` 501） | 以真 Bridge 的 P0 形狀回放 501 | **不改**（回放形狀仍有效，因 `not_implemented` 保留，D-111）；僅註解「唯一還回 501 的是 P1 的 tcs-draft」於 P1 訂正為歷史陳述 | `not_implemented` 的映射測試仍須綠 |
| 12 | `ResearchApiIT` 的 `records/audit` 斷言（P0 AT-960-4-3：`missing` 恆含 R7、R8、R11） | `missing` 含 R7、R8、R11 | 新增 P1 口徑案例（AT-961-21-1）；P0 案例改為「未分流專案」的條件式（口徑不變：未分流專案 `missing` 仍含 R7、R8、R11） | R7、R8 在 P1 可有列（`orchestrator.py:1193` 兩項 `absent_check` 換真比對） |

### 4.2 Bridge 既有測試與 product 連動（PKG-BR-D1、PKG-BR-D2）

| # | 檔:行 | 現值 | 改後值 | 為何現值變了 |
|---|-------|------|--------|--------------|
| 13 | `AgentConsole/engine-bridge/tests/test_research_capability.py:43`（`CAPABILITY`）、`:228-236`（非 exec 模組不得 subprocess；研究面禁 git 與 gh 字面）、`:267`（實樹與登記表一對一）、`:277-280`（net 類別）、`:295-297`（實樹無 git 與 gh argv 字面）、`:310-317`（紅綠自證夾具） | 研究面不得出現 git 與 gh 子行程 | **例外（改規則）**：新增類別 `vcs` 登記 `research/gitops.py`；「研究面不呼叫 git 或 gh」改寫為「git 與 gh 的 argv 字面只准出現在 `research/gitops.py`」；`CAPABILITY` 增列 `route.py`、`scaffold.py`、`gitops.py`、`scr.py`、`decompose_plan.py`；自證夾具同步 | `gitops.py` 必然違反原禁令（AT-961-8-5；PKG-BR-D1 先、BR-D2 後） |
| 14 | `AgentConsole/engine-bridge/tests/test_research_ast_locks.py:30`（`EXEC_MODULES`）、`:298`、`:315-327`（`create_key` 呼叫者集合：`create_project`、`_retry_init`、`_abandon_and_reinit`；註解「:route 屬 P1」） | 呼叫者三處 | `EXEC_MODULES` 加 `research/gitops.py`；**例外（改規則）**：C2（`:131-136`，`spec_frozen` 與 `approve_baseline` 呼叫只准住 `routers/research.py` 的 HTTP 處理函式）白名單加 `research/adopt.py`，限內環鍵與 `--stage Stage-1`，紅綠自證夾具（`:193-217`）補一正一負（D-126）；**例外（改集合）**：`create_key` 呼叫者終點加 `adopt.adopt_baseline`（集合大小 4）；新增 AST 鎖（`apply_minor` 不呼叫 `approve_baseline`；HEALING_FAILED 分支零 FSM 寫入；gitops 外無 git 與 gh） | AT-961-8-6 |
| 15 | `AgentConsole/engine-bridge/tests/test_research_router.py:290-291,321,328`、`test_research_settings.py:227,230,242-256`、`test_health_deep.py:76` | `scaffold_root is None`、`scaffold_templates == []`；`gh_cli.authenticated` 為 `NOT-EVALUABLE`；八鍵與十三鍵鍵集合 | 鍵集合斷言不動（八與十三）；`scaffold_root`、`scaffold_templates`、`repo_writable` 的值斷言改為依設定的實值（未設 scaffold 根時仍為 null 與空）；`gh_cli.authenticated` 斷言不動 | AT-961-16-1、16-2（只改預期值） |
| 16 | `AgentConsole/engine-bridge/app/routers/research.py:71-73,257-259,610`（`tcs-draft` 的 501 分支）與 `tests/test_research_router.py` 內 501 案例（現查） | `tcs-draft` 回 501 `not_implemented` | 移除分支；501 案例改為「`tcs-draft` 於前置不成立回 409」；`_not_implemented` 函式保留 | AT-961-9-1（D-111：reason 保留） |
| 17 | `AgentConsole/engine-bridge/app/research/orchestrator.py:1193`（`absent_check("task_decomposition")`、`absent_check("route_decision")`）、`gates/reconcile.py:44` 與 `tests/test_research_reconcile.py` 的 AT-960-21-1 | 兩項兩側皆缺席 ok | 兩項取真比對；既有 `present: false` 斷言對「無分流與拆解」專案仍成立（不改測試），新增案例見 AT-961-20-1、20-2 | AT-961-20 |
| 18 | `AgentConsole/engine-bridge/app/sdd_cli.py:358-366,478-482` 與 `tests/test_sdd_cli.py:365,390-394`、`test_research_fsm_ops.py:280,284` | `HUMAN_PENDING` 採納值只准 `baseline adoption` 前綴；動詞集合釘選 | 新增第二個前綴 `tcs gate`（D-97）；`test_sdd_cli.py` 零改動仍綠（動詞表不變）；新正負控放在既有 `test_research_fsm_ops.py` 末尾（BR-D2） | AT-961-7-7、8-7 |
| 19 | `AgentConsole/engine-bridge/tests/test_sdd_freeze.py:336` | `:freeze` 無 TCS 回 422 `missing_tcs` | **不改**；必須仍綠 | AT-961-9-5 |
| 20 | `AgentConsole/engine-bridge/tests/test_research_ast_locks.py` 與 `app/` 全樹 `rglob("*.py")`（`:157-159`）、`test_research_capability.py` 的實樹掃描 | 掃 `app/` 全部 `.py` | **不改掃描**；範本內 Python 檔改以 `.tmpl` 後綴存放（展開時去後綴），並於 `engine-bridge/pyproject.toml` 的 package-data 納入範本目錄（現查，屬 PKG-BR-D1） | 否則範本的 `app/main.py` 與 `tests/test_smoke.py` 會被 AST 鎖解析並要求 `CAPABILITY` 登記（AT-961-2-5、6-1、8-5） |
| 21 | `routers/research.py:120`（`reap_orphans`）與其測試 | 只回收 stage run | 加 `reap_route_orphans`（BR-D1 提供、BR-D2 接線）；測試只增 | AT-961-4-7 |
| 22 | `AgentConsole/engine-bridge/tests/test_research_compile.py:77,105,127-229` 的角色與 stage 清單 | `research`、`draft`、`review`、`revise` | 只增 `tcs-draft`（spec-engineer）；既有斷言不動 | AT-961-9-2 |
| 23 | 根層：`tools/tests/test_platform_neutral_paths.py` 的 `TestDirEntryPrimitivesAreAccountedFor`、`TestTextIoDeclaresEncoding`、`TestForeignExecutableArgvIsGuarded` | 新 Bridge 檔進入掃描母體 | **不改**（開發棒不得碰）；新程式必須遵守：不新增目錄項原語、文字 I/O 帶 `encoding`、`app/` 內不得出現 `powershell.exe`／`cmd` 假 gh 殼 | AT-961-23-2、23-4（`copyfile` 與 `copy2` 不在原語表，`copytree` 內部亦不用 rename，以工具實跑為準） |

### 4.3 frontend 既有測試與 product 連動（PKG-FE-D1、PKG-FE-D2、PKG-FE-W）

| # | 檔:行 | 現值 | 改後值 | 為何現值變了 |
|---|-------|------|--------|--------------|
| 24 | `AgentConsole/frontend/lib/api/endpoints.test.ts:288`（`toHaveLength(109)`）與 `EXPECTED`；**元鎖** `lib/api/si.endpoints.test.ts:46`（字串 `expect(names).toHaveLength(109);`） | 109 個端點函式，元鎖釘該字串 | `EXPECTED` 加九個函式，總數 118（`:288` 與標題含「109」字樣的 `it` 標題同步改）；`si.endpoints.test.ts:46` 同批改為 118；兩檔同包同改，只改一邊必紅 | 前端 API 層新增九個函式（AT-961-19-5；先例同 P0 §4 第 10 列） |
| 25 | `AgentConsole/frontend/components/domain/research/ResearchWorkspaceView.test.tsx:21,90,188,207-250`（AT_960_19_5 的 `PLACEHOLDERS`：route、build、deliver 三個參數）與 `:241`（超前導回） | 步驟 3 至 5 皆占位 | **例外**：占位參數只留 `deliver`；route 與 build 改驗真面板（`RoutePanel`、`BuildFrontPanel`）；超前導回案例沿用；標題與 id 不變 | 占位換真面板（AT-961-19-1） |
| 26 | `AgentConsole/frontend/tests/e2e/research-docker.stack.spec.ts:240,302-313` 與 `tests/e2e/README.md:224`（AT_960_22_5「步驟 3～5 占位」） | route 為占位面板 | 預期改為「步驟 5 占位、步驟 3 與 4 為真面板」；其餘斷言零改動；P1 新增案例放新檔（AT-961-22-8） | 同上 |
| 27 | `AgentConsole/frontend/lib/domain/research.ts:127-152`（`FLOW_PHASE_LABEL`、`FLOW_PHASE_DERIVED`、`FLOW_VOCABULARY_KEYS`）與其測試、說明登記表詞彙（`lib/help/research-workspace.ts`）、`stateKeys.test.ts` 的 `researchFlow` 上游對拍 | 缺 `BUILD_READY`、`PAUSED`、`SCR_OPEN` 三個衍生相態標籤 | 補三值（D-114：「可開始建置」、「已暫停」、「SCR 進行中」）與 `ROUTING`、`ROUTED` 標籤；詞彙鎖與狀態表同步 | AT-961-19-3、19-E-1 |
| 28 | `AgentConsole/frontend/lib/domain/research.ts` 的 `RESEARCH_REASONS` 與 `lib/api/reasons.test.ts`、`lib/api/reasons.ts` | 22 個 | `RESEARCH_REASONS` 加 13 個（9＋R-2 的 4）；`reasons.ts` 與 `reasons.test.ts` **不改**（研究 reason 不入共用表） | AT-961-15-4、19-5 |
| 29 | `AgentConsole/frontend/tests/fixtures/research/misc.ts:9-14`（capabilities 夾具：`ghCli.ok` 假、`scaffoldRoot` null、`scaffoldTemplates` 空）、`tests/helpers/research.tsx` | P0 夾具 | 只增：全可用與各缺項的 capabilities 夾具、路由與拆解與 SCR 的 DTO 黃金檔 | AT-961-16-5 |
| 30 | `frontend/tests/design-rules.test.ts:27-76`、`components/layout/layout.test.tsx:43-61`、`components/domain/si/si.static.test.ts:252-275`、`lib/domain/sysadminBackup.test.ts:331-333`、`lib/nav/registry.test.ts`（mobile 上限 6）、`lib/help/registry.test.ts`、`content.test.ts` | 靜態鎖與計數鎖 | **不改**；P1 新增與增修的檔必須遵守（無陰影與漸層、只用 token、無手寫 svg、無 emoji、無 outline-none、無 dark:、四區塊名不出現在 `app/research/**`、無 Bridge 埠號字面、`queries.ts` 只增不動既有兩行輪詢常數）；P1 無新路由與導覽列，`HELP_PAGES` 22、`HELP_ROUTES` 25、`StateTableId` 19 不變 | AT-961-19-2、19-6 |

| 31 | backend：`ResearchFlowPolicyTest`、`ResearchApiIT` 的 fsm 視圖與詳情斷言、`ResearchFsmViewDto` 與 `FsmView` 記錄（現查）；既有 SDD freeze 服務與其 IT（類別現查） | 無 `stage2Frozen`；freeze 成功後不呼叫 Bridge | `FsmView` 加 `stage2Frozen`（由 `frozen_stages` 導出），斷言只增鍵；freeze 服務成功後對綁研究專案的專案呼叫 Bridge `:reconcile`，既有 freeze 斷言與回應位元組不變 | D-125（AT-961-25-1、25-3）；PKG-API-P1 |
| 32 | Bridge：`gates/reconcile.py`、`orchestrator.py` 的對帳與 `tests/test_research_reconcile.py` 的 AT-960-21-2 對映表案例 | 對映表無 `pending_correction` 第三態 | 增第三態與 `TCS_PENDING × Stage-2` 校正；既有列結果不變 | D-121、D-125（AT-961-20-3、25-2）；PKG-BR-D2 |
| 33 | frontend：`BuildFrontPanel` 測試與 `tests/fixtures/research/**`（`stage2Frozen` 夾具） | 無「重新對帳」 | 只增 | D-125（AT-961-25-4）；PKG-FE-D2 |

| 34 | `AgentConsole/backend/src/test/java/com/aisdlc/console/infrastructure/persistence/ResearchSchemaMigrationIT.java:463-464`（`newDatabase()` 與 `databaseAt("15")`）、`:495`（`added` 須等於 `RESEARCH_TABLES` 十三張，訊息「V16～V18 恰多出 13 張表」）、`:518`（`guardsByTable.keySet()` 須等於 `RESEARCH_TABLES`）、`:1385-1389`（引用 `research_controlled_update_guard` 的表須等於 `CONTROLLED_TABLES` 五張）、表清單常數 `:59-67` | 十三張／五張；V16～V18 字樣 | **例外（改規則）**：`RESEARCH_TABLES`、`CONTROLLED_TABLES` 兩個 P0 常數不動；新增 `V19_TABLES`（五表）與 `V19_CONTROLLED_TABLES`（四表：`research_route_decisions`、`research_route_steps`、`research_scr`、`research_decompositions`；`research_deliveries` 屬 append-only 清單）；`:495` 釘 `databaseAt("18")` 對 P0 十三張並另立 V19 增量斷言（`databaseAt("19")` 對 `V19_TABLES`）；`:518` 與 `:1385-1389` 的期望集合改為 P0 集合＋V19 集合；`:1377` 的受控表迴圈不動（`rowIds`／`CONTROLLED_UPDATE_COLUMNS` 只含 P0 五表；V19 四表由 AT-961-1-8 自備定位另驗）；訊息字樣 V16～V19 | V19 落地使三處既有斷言對正確實作必紅（QA 覆蓋審 F-01；AT-961-1-1）；PKG-DB-P1 |
| 35 | `AgentConsole/backend/src/main/java/com/aisdlc/console/adapter/in/web/dto/research/ReconcileResultDto.java:29`（Schema「ok｜drift｜NOT_EVALUABLE」）與 `ResearchApiIT`／`OpenApiIT` 的對帳說明斷言（現查） | 三值 | 加第四值 `pending_correction`（只改說明字樣與預期值） | D-121、D-125（AT-961-20-E-3、F-12）；PKG-API-P1 |
| 36 | frontend：`lib/domain/research.ts:525-534` 的對帳判讀與其測試 | 只認 `drift` | 只增：`pending_correction` 不計漂移的案例（AT-961-20-E-2，F-12） | 同上；PKG-FE-D2 |

### 4.4 凍結文件的勘誤（不得改凍結檔；主控於 RELEASE_READY 的 refreeze 批次各補一列勘誤；方向依 D-115 與 RISKS (b)）

| # | 凍結檔:位置 | 現有陳述 | 勘誤內容 |
|---|-------------|----------|----------|
| E1 | `TCS-ResearchToPRD-P0-20261102.md`：AT-960-2-7、AT-960-13-3、AT-960-5-6、AT-960-19-5、AT-960-22-5 與 §5.1 錯誤 reason 列 | `scaffold_root` P0 恆為 null；`create_key` 呼叫者三處、「:route 屬 P1」；22 個 reason；步驟 3 至 5 占位 | 依本檔 §4：值語意改依設定、呼叫者加 `adopt.adopt_baseline`、reason 增為 35、占位只留 deliver；P0 的 AT 編號與數不變 |
| E2 | `API_Contract_ResearchToPRD.md` §0.2、§1.1、§1.2、§1.3、§1.4、§2.2 | 缺 API-RP-24／25 與 scr apply、`:decompose`、`:decomposition-signoff`、`:route-compensated`、`:scr-apply`；`route` 回 202；`route.targetPath` 為使用者欄；SCR 缺 `reasonClass`；無 `DecompositionDto`；`approve` 缺 `versionBump` | D-94、D-103、D-105、D-106、D-112、D-113、D-115：補列、`route` 改 200、退役 `targetPath` 並加 `owner`、`ci`、`dockerCompose`、`projectName`、補 `DecompositionDto`、`approve` 加選填 `versionBump`；§0.2 reason 表補 13 項 |
| E2b | `API_Contract_ResearchToPRD.md` API-RP-18 與 §1.3 `ReconcileResult` | `checks[].status` 值域 `ok｜drift｜NOT_EVALUABLE` | 加第四值 `pending_correction`（`TCS_PENDING × Stage-2 已凍結` 的待校正，D-121、D-125；不計 drift）；連動 `ReconcileResultDto.java:29` 的 Schema 說明（AT-961-20-E-3）與前端判讀（AT-961-20-E-2） |
| E3 | `ADR-003-ResearchToPRD.md` D8、D16、§4 | worktree 位置未定；D16 白名單無 `add --`、`worktree list`、`-c core.longpaths=true`、`GIT_COMMITTER_*` | D-95、D-99：`BRIDGE_WORKTREE_ROOT` 預設與逐次 `-c`；補列白名單與環境；`GIT_TERMINAL_PROMPT=0`、`GCM_INTERACTIVE=never` |
| E4 | `ADR-XPLAT-017-bridge-fsm-write-surface.md` D2 表、D4、附錄 A | `transition --to HUMAN_PENDING` 只准 baseline adoption；內環鍵「沿既有行為」 | D-97：加第二個理由前綴 `tcs gate`；D-45 的「P0／P1 不呼叫 gate」與 SCR 序列的 `gate` 並存（⚖P1-27） |
| E5 | `ResearchToPRD_PRD.md`：AC-R2P-12-3（:667「ADMIN 維護」）、FR-R2P-19 邊界（:799「同一 Stage」）、AC-R2P-19-1（內環鍵回 IMPLEMENTATION）、AC-R2P-13-2 與 13-5（副本含 raw 與 ls-files 排除）、FR-R2P-14（:709 談判動詞在研究面白名單） | 見左 | D-100（固定四值常數）、D-104（同一研究專案保守計）、D-115(b)-7（現態不變）、D-117（副本含 raw、`.gitignore` 排除）、(b)-14（談判由既有 `/autoclaude/runs` 的 sdd 區塊驅動，研究面不呼叫） |
| E6 | `Architecture.md` §11.1 研究 reason 表、§11.3′／K.4、§5.4 | 22 個 reason；DDL 無需改 | 補 13 個 reason 與狀態碼；K.4 不改（D-116：P1 不需 V20）；R7、R8 參數 JSON 與 waivers 以 `research_artifacts(kind=ROUTE_DECISION／TASK_DECOMPOSITION)` 承載 |
| E7 | 四份凍結 TCS 的導覽「恰 N 項」陳述（P0 §4.4 已涵蓋） | — | P1 無新導覽列，**不需新勘誤**（記於此以示已核對） |

> **落地記錄（RELEASE_READY 勘誤批次，11-07）**：E2～E6 已落地於各上位文件的勘誤表與正文（API 契約第 22～34 號、PRD 第 17～26 號、ADR-003 第 6～10 號、ADR-XPLAT-017 第 3～5 號、Architecture §11.1 與 §11.3′ K.5／K.6）；E1（凍結的 TCS-P0 自身勘誤表）與 E3 的 TCS 側不在本批範圍，維持待辦。

### 4.5 硬釘掃描（掃描指令與逐字結果見自查檔 `HARDPIN_SCAN.txt`；對 `backend/src/test`、`backend/src/main`、`frontend/lib`、`frontend/components`、`frontend/tests`、`engine-bridge/{app,tests}` 重掃）

> 判準：既有測試以「精確集合、個數、原始碼字串、全樹 AST 或文字掃描」釘住某個會因本期而變的事實。本輪掃過：Flyway 版本清單、既有表快照、`OpenApiIT` 計數、reason 集合、RBAC 清單、`SecurityConfig` 規則、capabilities 停用值、AST 鎖與能力登記、動詞表釘選、`tcs-draft` 501 骨架、對帳兩項、端點函式總數與元鎖、占位面板測試、詞彙鎖、說明登記表。逐筆判讀：上列 §4.1 至 §4.3 各列；其餘命中與本期無關（見自查檔）。

---
## 5. 測試資料規格

### 5.1 值域常數（測試與產品碼共用同一份常數，不各寫一份；初值標「未校準」者以常數登記並以測試釘住）

| 常數 | 值 | 來源 |
|------|-----|------|
| 軌道 | `A`、`B` | PRD FR-R2P-11；V19 |
| `BRANCH_PATTERN` | `^feature/[a-z0-9-]{1,40}$`；預設 `feature/issue-<NNNN>`（NNNN＝`rp_no` 零填四位）；另須合 git ref 規則 | 契約 §1.2；ADR-003 D16；PRD FR-R2P-12 |
| `REPO_NAME_PATTERN` | `^[a-z][a-z0-9-]{1,38}$`（2 至 39 字元；明示給值時）；省略時取 `project_name` | 契約 §1.2；D-119 |
| `PROJECT_NAME_PATTERN` | `^[a-z][a-z0-9-]{1,61}$`（2 至 62 字元；同時合 GitHub repo 名與 FSM 鍵文法） | D-119 |
| `OWNER_PATTERN` | `^[A-Za-z0-9][A-Za-z0-9-]{0,38}$` | D-106（本檔類推） |
| `visibility` | `PUBLIC`、`PRIVATE`，預設 `PRIVATE`；`PUBLIC` 須 `confirm_repo_name` 等於 `repo_name` 且僅軌道 B | 契約 §1.2；D-15；V19 CHECK |
| `PLACEMENT_TARGETS` | `autoclaude`、`agentconsole`、`sdd`、`monorepo`（每項附一句取自 `Root_Layout_and_Module_Placement.md` §2 的出處）；擴充＝改 SSOT 與 CHECK（V20） | D-100；V19 CHECK |
| 內環鍵 | 軌道 A `<module>-<slug>`（module 為小寫模組名）、軌道 B `<project-name>`；文法 `^[a-z][a-z0-9-]{1,99}$`（D-119）；子專案目錄映射 autoclaude→`AutoClaude`、agentconsole→`AgentConsole`、sdd→`AISDLC_SDD/<LATEST>`、monorepo→根 | IFACE §4.2；BRIDGE §8.0 |
| `scope_differs_reason` | 1 至 200 字，僅分流軌道與 PRD `target_scope` 不同時必填 | 契約 §1.2 |
| 理由上限 | SCR 理由、拆解豁免理由、補償理由皆 1 至 500 字（三個獨立常數 `SCR_REASON_MAX`、`WAIVER_REASON_MAX`、`COMPENSATE_REASON_MAX`） | PRD AC-R2P-19-5；契約 §1.2 |
| `TEMPLATE_VAR_PATTERN` | `[A-Za-z0-9_-]`（範本變數字元集）；輸出路徑 `resolve()` 後須在新根之下 | PRD AC-R2P-13-8；ADR-003 D14 |
| 範本登記 | `app/research/scaffold_templates/<name>/`（名稱合 `[A-Za-z0-9_-]`）；P1 僅 `python-fastapi`；範本內 Python 檔以 `.tmpl` 存放 | D-32；⚖P1-18 |
| 路由步驟名 | `VALIDATE_TARGET`、`GIT_SWITCH`、`SCAFFOLD_FILES`、`GIT_INIT`、`GIT_COMMIT`、`GH_REPO_CREATE`、`PUBLISH_DOCS`、`COPY_WORKSPACE`、`REGISTER_STUB`、`IMPL_KEY_INIT`、`BASELINE_ADOPT`（十一個；軌道 A 序：VALIDATE_TARGET、GIT_SWITCH、PUBLISH_DOCS、REGISTER_STUB、GIT_COMMIT、IMPL_KEY_INIT、BASELINE_ADOPT；軌道 B 序：VALIDATE_TARGET、SCAFFOLD_FILES、COPY_WORKSPACE、GIT_INIT、GIT_COMMIT、〔GH_REPO_CREATE〕、IMPL_KEY_INIT、BASELINE_ADOPT） | V19 CHECK；IFACE §4.2、§4.3 |
| 路由與步驟狀態 | 路由 `PENDING`、`RUNNING`、`SUCCEEDED`、`FAILED`、`COMPENSATED`；步驟 `RUNNING`、`OK`、`FAILED`、`SKIPPED`、`COMPENSATED`（P1 不產生 `SKIPPED` 列） | V19 CHECK |
| 分流執行 | Bridge 牆鐘 `BRIDGE_ROUTE_TIMEOUT_SECONDS`＝300；console-api 對 `route` 與 `decomposition` 的 Bridge 讀逾時 330 秒；其餘研究寫入 30 秒；連線逾時 2 秒 | D-105 |
| 路徑根 | `BRIDGE_WORKTREE_ROOT` 預設 `<BRIDGE_RESEARCH_ROOT>/_worktrees`；`BRIDGE_SCAFFOLD_ROOT` 無預設（未設＝軌道 B 停用）；`BRIDGE_REPO_ROOT` 覆寫 `repo_writable()` 的判斷根（未設＝現行 `REPO_ROOT`）；三者自動併入 allowed roots | D-95、D-96 |
| gitops 環境 | `GIT_AUTHOR_*`、`GIT_COMMITTER_*`、`GIT_TERMINAL_PROMPT=0`、`GCM_INTERACTIVE=never`；唯讀 git 呼叫另帶 `GIT_OPTIONAL_LOCKS=0`；`GH_TOKEN` 只傳 gh；移除 `BRIDGE_*`、`SDD_*`、`PYTHONPATH` | D-99；ADR-003 D16 |
| 採納序列 | `show`（建檔）＋5 次 `transition`（SCENARIO_DETECT、AGENT_LOAD、SPEC_DRAFTING、SCG_VALIDATION、HUMAN_PENDING；reason 前綴 `baseline adoption`）＋`spec-frozen --stage Stage-1` | PRD AC-R2P-11-7；IFACE §5.1 |
| Stage-2 序列 | `transition SPEC_DRAFTING`→（stage run）→`transition SCG_VALIDATION`→`transition HUMAN_PENDING`（reason 前綴 `tcs gate`）→既有 `:freeze` | D-97、D-109 |
| TCS 草擬 | agent `spec-engineer`；輸入 `03_execution/tcs_inputs.json`；輸出 `03_execution/tcs_draft.md`；發佈 `docs/03_testing/contracts/TCS-<slug>-<yyyymmdd>.md`；失敗 `exit_reason` 為 `tcs_invalid` | D-109；IFACE §1.3 |
| 拆解 | 每次呼叫步驟 ≤24、無環、prompt 非空（`max_steps`、`cycle`、`empty_prompt`，另 `brain_failed`、`brain_unsupported`）；`covers_ac` 由呼叫綁定的 AC 清單賦值；INT 總耗時中位數大於 120 秒列症狀 | PRD FR-R2P-14；D-94 |
| 拆解狀態 | `DRAFTED`、`SCG_PASSED`、`FROZEN`、`IMPORTED`（P1 不用）、`SIGNED_OFF`、`REJECTED`、`STALE` | V19 CHECK；D-113 |
| SCR | `kind`：`MINOR`、`MAJOR`；`source_kind`：`HUMAN`、`REVIEW_FINDING`、`SCG4`、`HEALING_FAILED`；`reason_class` 對映：PRD 缺漏證據→`EVIDENCE`、AC 模糊→`AC_VAGUE`、需求變更→`REQ_CHANGE`、技術不可行→`INFEASIBLE`、其他→`OTHER`；`status`：`OPEN`、`APPROVED`、`REJECTED`、`APPLIED`、`SUPERSEDED`；`SCR_MINOR_MAX`＝2（同研究專案、MINOR、OPEN／APPROVED／APPLIED 計） | PRD FR-R2P-19；D-104；V19 CHECK |
| SCR Stage 名與版本 | `Gate-0-SCR<k>`；新 PRD 版本 `v1.<n>.0`，`versionBump` 為 `MAJOR` 時 `v2.0.0` | PRD §5.1.9；D-115 |
| 內環現態矩陣 | 直接起跑：IMPLEMENTATION、EXECUTION_EVALUATION、ADVERSARIAL_EVALUATION、PR_REVIEW（SPEC_AUDIT 略過第一個 transition）；先 gate FAIL：RTM_VERIFY、RELEASE_READY；其餘 409 | PRD FR-R2P-19；ADR-XPLAT-017 附錄 A |
| 游標值 | 執行中 `route`／`ROUTING`／`RUNNING`；成功 `build`／`ROUTED`／`IDLE`；失敗 `route`／`ROUTING`／`FAILED`（`flow_detail`＝失敗步驟名）；SCR `studio`／`SCR_OPEN`；TCS `TCS_DRAFTING`、`TCS_PENDING`；衍生 `BUILD_READY`「可開始建置」、`PAUSED`「已暫停」、`SCR_OPEN`「SCR 進行中」（衍生不入對映）；TCS 凍結後校正 `build`／`ROUTED`／`IDLE`（`research.step` 的 `reason` 為 `tcs_frozen_correction`）、讀端衍生 `build`／`BUILD_READY`／`IDLE` | D-105、D-114、D-121、D-125；V16 CHECK |
| 新 reason（P1 九個） | `route_unsupported_in_deployment`（422）、`branch_exists`（409）、`target_not_empty`（422）、`public_confirmation_required`（422）、`route_conflict`（409）、`route_step_failed`（502）、`scr_open`（409）、`scr_limit`（409）、`decomposition_stale`（409）；R-2 尾巴四個：`compile_failed`（503）、`sdd_cli_failed`（502）、`fsm_state_unreadable`（422）、`invalid_request`（422）；總數 22＋4＋9＝35 | 契約；D-115；⚖P1-25 |
| 預演缺項 | `details.missing[].item`：`git`、`gh`、`repo_writable`、`scaffold_root`、`scaffold_templates`、`worktree_root`、`gh_auth`（僅 `create_github` 為真） | IFACE §1.1；D-98、D-122 |
| PRD 發佈路徑 | 軌道 A：`<子專案根>/docs/01_requirements/<slug>_PRD.md`（slug 原樣）；軌道 B 不另發佈（採納 `my-project/<slug>/01_specs/PRD-v1.0.0.md`） | D-119 |
| 唯讀提示 | `title` 為「權限不足（唯讀角色）」 | TCS-ExecMonitorEntry W-E1 先例；P0 W-R9 |
| 端點計數 | `OpenApiIT` 路徑 107、操作 124；`endpoints.test.ts` 118；自算法見 AT-961-15-3 與 AT-961-19-5 | §4 第 3、24 列 |

### 5.2 夾具倉（路徑相對 `AgentConsole/engine-bridge/tests/`，凍結複本、hermetic、無網路）

- **拋棄式 git 夾具** `research_git_support.py`（BR-D1 新增；`GIT`）：兩種來源，測試選其一並把選擇寫進證據——(1) `git clone --no-hardlinks <monorepo 根> <暫存目錄>`（保留歷史與 `main`）；(2) `git archive HEAD` 匯出到暫存目錄再 `git init -b main` 與一筆初始 commit（無歷史，基底 ref 取該 `main`）；兩種皆只對真 repo 做唯讀操作（`git clone` 讀、`git archive` 讀），測試前後真 repo 的 `HEAD`、`git status --porcelain` 與 `.git` 位元組不變；`HOME` 與 `GIT_CONFIG_GLOBAL`、`GIT_CONFIG_SYSTEM` 指向暫存空檔以隔離使用者設定；收尾清除暫存 clone 與 worktree（先 `git worktree remove` 再刪目錄；Windows 先單獨刪 `node_modules` junction）。
- **假 gh 夾具** `fixtures/research/fake_gh/**`（`GH`）：Windows 形態為 `gh.cmd`（薄殼轉呼叫 `python gh_fake.py %*`）、POSIX 形態為可執行的 `gh`（sh 腳本）；皆以 PATH 前置使 `shutil.which("gh")` 解析到夾具；行為表由 JSON 夾具與環境變數 `FAKE_GH_MODE` 切換：`ok`（預設；`auth status` rc 0、`repo create <o>/<r> --private|--public --source . --push` rc 0 並輸出假 URL）、`unauth`（`auth status` rc 1）、`fail-create`（`repo create` rc 1）、`leak`（刻意把 `GH_TOKEN` 值印到 stdout 與 stderr，模擬 gh 洩漏）；每次呼叫在夾具記錄檔追加一行：argv（不含 token）、環境鍵名單、「環境中有 `GH_TOKEN`＝是／否」；**PowerShell 與 POSIX 兩形態都入庫，只有本平台那份在本機實跑，另一平台標「未驗」**（NFR-R2P-10-3）；`app/` 內不得出現 `powershell.exe`／`cmd` 假 gh 殼。假 token 字面：`ghp_FAKE_R2P1_TOKEN_000000000000000000`。
- **範本夾具** `fixtures/research/scaffold/`：一份含 `node` 的夾具樹（證明清單來自目錄）、非法名稱與空目錄各一；期望檔案清單黃金檔（`python-fastapi` 展開後的相對路徑集合）。
- **落點夾具** `fixtures/research/placement/`：`Root_Layout_and_Module_Placement.md` §2 的副本（四項與各自出處句）與一份 PRD 的「模組落點表」。
- **拆解引擎夾具** `fixtures/research/decompose/`：沿既有 `DecomposeService` 的二段拆解形狀的回放檔（每個 US 一份固定樹）；四個變體（恰 24 步、25 步、含環、空 prompt）；夾具模型輸出刻意帶錯誤的 `covers_ac`（驗證不被採信）；三個 Goal 各 20 步的大型變體。
- **研究劇本** `fixtures/research/scripts/`：既有 `mock_claude_script_fail3.json` 與 `mock_claude_script_pass.json` 增 `(tcs-draft, 0)` 步驟與 `tcs_*.json` 變體（合法；缺 AC；孤兒 AT；判定指令空；含假機密；檔名不合）；格式沿 P0（`role`、`round`、`writes`），不改既有鍵。
- **框架側夾具副本** `fixtures/research/framework/`：沿 P0，增 `TEST-CONTRACT-SPEC-TEMPLATE.md` 副本（tcs-draft 預檢規則取自它），整合 P1 時以框架成品逐位元組對拍。
- **資料庫夾具** `research_pg_support.py`：`make_research_db()` 套到 V19。FSM 夾具延用 `tests/fake_sdd.py`（只增，內環鍵邊表鏡像與對拍鎖）與計畫書附錄 A 形態的暫存狀態目錄。
- **backend 夾具**（`AgentConsole/backend/src/test/resources/research/`）：Bridge 回應黃金檔（snake_case）與 camelCase 對照；`MiniBridge` 補 `:route-preview`、`:route`、`:route-compensated`、`:scr`、`:scr-apply`、`:decompose`、`:decomposition-signoff` 與 `/sdd/fsm` 視圖。**frontend 夾具**（`AgentConsole/frontend/tests/fixtures/research/`）：capabilities 各缺項、路由與拆解與 SCR 的 DTO 黃金檔、SSE 事件流。

### 5.3 hermetic 環境

- 一律無網路外呼：真 git 只在 `$env:TEMP` 下的拋棄式 clone；`gh` 一律假夾具；headless claude 一律 `FC` 或 `aisdlc-mock-claude`；GitHub、PyPI、arXiv 等真端點在任何 AT 中都不被連線（AT-961-23-E-1 以替身驗證）。真網路只出現在 V-R8 與 V-H3（掌舵者真機）。
- DB 型 AT 只用拋棄式資料庫（`RDB` 或 Testcontainers），絕不連真 `aisdlc` 資料庫；真 `~/.autosdd/`、真 `AgentConsole/build/reports/fsm`、真工作區根、真 repo 一律唯讀；FSM 實跑一律在暫存狀態目錄。
- 時間以假時鐘注入（限流、逾時、心跳、SSE 緩衝、讀逾時 330 秒）；任何測試不得 `sleep` 超過 2 秒等待真時間；分流同步執行的 300 秒牆鐘以假時鐘注入驗證，不真等。
- 清理義務（掌舵者 2026-11-07 指令）：每個整合與 INT AT 收尾清掉自建的 subst 磁碟機、副本目錄、worktree、行程、拋棄式資料庫、Docker 測試標籤與懸空卷；證據檔列「殘留清單」（沒有寫「無殘留」）。

### 5.7 允許變更的檔案集合（各包開發 agent 只准動自己包的檔；路徑相對 monorepo 根；本節為 PACKAGES 第二版 §1 的收斂，兩者不一致以較窄者為準並回報主控）

> 共同禁區（任何包皆不得動）：根 `CLAUDE.md`、`.claude/`、`tools/`、`.github/`、`AutoClaude/`、`AISDLC_SDD/`（含 LATEST）、`AgentConsole/CLAUDE.md`、`docs/**`、`AgentConsole/docs/**`（文件一律由主控與 SD 寫；開發棒零文件）、`.gitignore`、`package.json` 與 `package-lock.json`（P1 預期零新相依）、`docker-compose*.yml`、`Dockerfile`、`AgentConsole/docker/**`（含 nginx：既有 `/api/` 的 `proxy_read_timeout 86400s` 無需改，D-105）、Flyway 已發佈檔 V1～V18、`engine-bridge/app/decompose.py` 與 AutoClaude 的拆解程式（零改動，D-94）、`routers/sdd.py`。共享單點：`OpenApiIT` 計數與 `ResearchReasonsTest` 名單只給 PKG-API-P1；`lib/api/schema.d.ts` 只給 PKG-FE-W；`lib/api/{endpoints,queries,types}.ts`、`ResearchWorkspaceView.tsx`、`lib/domain/research.ts`、說明登記表只給 PKG-FE-D1（FE-D2 僅增補明列者）；`test_research_capability.py` 與 `test_research_ast_locks.py`、`db.py`、`settings.py`、`main.py` 由 BR-D1 先、BR-D2 後（序列）；`orchestrator.py` 與 `gates/reconcile.py` 對帳兩項只給 BR-D2。

| 包 | 允許變更的檔案集合 |
|----|--------------------|
| PKG-DB-P1 | `AgentConsole/backend/src/main/resources/db/migration/V19__research_route_scr_delivery.sql`（新；逐字取 Architecture K.4，不得自改）；`backend/src/test/java/com/aisdlc/console/infrastructure/persistence/ResearchSchemaMigrationIT.java`（表清單常數與 V19 斷言）、`SchemaMigrationIT.java`、`V5UpgradeMigrationIT.java`、`IssuePriorityMigrationIT.java`、`BackupJobMigrationIT.java`、`SiConsoleWritesMigrationIT.java`（只改版本清單；`BackupJobMigrationIT` 另改欄位查詢條件，§4 第 2 列）；`engine-bridge/tests/research_pg_support.py`（與其單元測試） |
| PKG-BR-D1 | `AgentConsole/engine-bridge/app/research/{route,scaffold,gitops,adopt}.py`（新；`adopt.py` 為基線採納，D-126）、`app/research/scaffold_templates/python-fastapi/**`（新；Python 檔以 `.tmpl` 存放）、`app/routers/research_route.py`（新；含 `:route-preview`、`:route`、`:route-compensated`）、`app/main.py`（一行 include）、`app/research/settings.py` 與 `app/settings.py`（四個新設定與 capabilities 實值；十三鍵鎖不動）、`app/research/db.py` 與 `outbox.py`（分流 Op）、`engine-bridge/pyproject.toml`（範本 package-data）；測試 `tests/test_research_{route_gate,route_exec,route_a,route_b,scaffold,adopt,gitops,capabilities_p1}.py`、`tests/research_git_support.py`、`tests/fixtures/research/{fake_gh,route,scaffold,placement}/**`、`tests/test_research_capability.py`、`tests/test_research_ast_locks.py`（§4 第 13、14 列）、`tests/test_research_router.py`、`test_research_settings.py`、`test_health_deep.py`（只改預期值，§4 第 15 列）；`engine-bridge/README.md`（環境表四列；D-129）；**`app/sdd_cli.py` 與 `app/research/fsm_ops.py` 的 inner-create 擴充**（`create_key(inner=)`、`_run(inner_create=)`、`run_research_verb(inner_create=)`、`INNER_KEY_RE`／`is_inner_key`；**主控落地**，預設行為不變，D-129）；不得動 `routers/research.py`、`compile/*` |
| PKG-BR-D2 | `AgentConsole/engine-bridge/app/research/{scr,decompose_plan}.py`（新）、`app/routers/research_scr.py`（新；`:scr`、`:scr-apply`、`:decompose`、`:decomposition-signoff`）、`app/routers/research.py`（移除 tcs-draft 501、`:approve-baseline` 的 open-SCR 分支與 `versionBump`、`reap_route_orphans` 接線；**追認集合外三處**：`tcs_unmet` 助手與 `TCS_*` 常數、檔尾 `include_router(research_scr)`、`reconcile_at_route` 助手〔`route_execute` 成功後的對帳呼叫點，主控落地〕——P0 呼叫點鎖與載入順序的必然連動，D-134(1)、(2)）、`app/research/orchestrator.py`（TCS_DRAFT 分派、對帳兩項）、`app/research/gates/reconcile.py`（含 `TCS_PENDING × Stage-2` 校正與第三態，D-125）、`app/research/gates/tcs_schema.py`（新，若需要）、`app/research/compile/{personas,playbooks,prompts}.py`（spec-engineer 變體）、`app/research/db.py`（SCR、拆解、TCS Op）、`app/research/export.py`（版本號規則）、`app/sdd_cli.py`（`tcs gate` 前綴）、`app/mock_claude.py`（不改既有鍵）；測試 `tests/test_research_{scr,scr_fsm,decompose,tcs_draft,reconcile,int_p1}.py`、`tests/test_research_{capability,ast_locks,compile,router,fsm_ops}.py`（只增與只改預期值）、`tests/test_mock_claude_research.py`（零改動）、`tests/fixtures/research/{scripts,decompose}/**` |
| PKG-API-P1 | `AgentConsole/backend/src/main/java/com/aisdlc/console/**` 中研究相關新檔（DTO、`RouteReadAdapter`、`ScrReadAdapter`、`DecompositionReadAdapter`、`ResearchRouteService`、`ResearchScrService`、`ResearchDecompositionService`、`DecompositionCoverage`）與既有檔（`ResearchController`〔或新 `ResearchRouteController`〕、`Research{Query,Command}{UseCase,Service}`、`BridgeHttpAdapter`、`BridgeEndpoints`、`RequestFactoryProvider`、`SecurityConfig`、`ErrorReasons`、`ResearchErrorDocs`、`ResearchFlowPolicy`、既有 execute 與 resume 啟動服務、設定鍵目錄、`ResearchProjectDetail`、`FsmView` 與 `ResearchFsmViewDto`、既有 SDD freeze 服務〔`routers/sdd.py` 零改動，只改 console-api 服務〕）；**V20（D-132）**：`backend/src/main/resources/db/migration/V20__research_github_token_config.sql`（新；只種 `system_configs` 一列，不改 V1～V19）、`ConfigCatalog` 登記 `research.github_token`、設定類 IT（`SettingsApiIT` 等釘 50 鍵者改 51，只改預期值）、六個版本清單 IT 加 `"20"`、`engine-bridge/tests/research_pg_support.py`（`LAST_VERSION` 加 20）；`backend/src/test/**` 中 `ResearchRouteApiIT`、`ResearchScrApiIT`、`ResearchDecompositionApiIT`、`DecompositionCoverageTest` 新檔與 `OpenApiIT`、`ResearchReasonsTest`、`RbacIT`、`ResearchApiIT`、`ResearchFlowPolicyTest`、`ResearchArchTest`、`ResearchBridgeShapeTest`、`MiniBridge*`（只增與只改預期值）、`src/test/resources/research/**` |
| PKG-FE-D1 | `AgentConsole/frontend/components/domain/research/{RoutePanel,RouteDrawer,RouteCardA,RouteCardB,RouteActionList,RouteStepsTimeline,PublicRepoConfirm}.tsx` 與測試、`BuildFrontPanel.tsx`（僅占位 stub）、`ResearchWorkspaceView.tsx`（一次接好 route 與 build 兩條分支）與 `ResearchWorkspaceView.test.tsx`（§4 第 25 列）、`FlowStepper.tsx` 與測試（SCR 與 route 標示）、`lib/domain/research.ts` 與 `research.test.ts`、`lib/api/{endpoints,queries,types}.ts` 與 `endpoints.test.ts`、`lib/api/si.endpoints.test.ts`（只改 `:46` 的釘值字串）、`lib/help/research-workspace.ts` 與 `lib/help/*.test.ts`（現查）、**追認集合外兩檔** `lib/help/states.ts`（`STATE_HELP.researchFlow` 須與詞彙同鍵）與 `lib/nav/research-nav.test.ts`（詞彙 27→28、衍生 5→6 的釘值；同 P0 D-69 體例，D-130）、`components/domain/help/stateSources.ts`（若詞彙需要）、`tests/fixtures/research/**`、`tests/helpers/research.tsx`、`tests/e2e/research-route.mock.spec.ts`（新）、`tests/e2e/a11y.mock.spec.ts`（增步驟 3 情境）；不得動 `schema.d.ts`、`package.json`、`app/layout.tsx`、`lib/nav/registry.ts` |
| PKG-FE-D2 | `AgentConsole/frontend/components/domain/research/BuildFrontPanel.tsx`（填實；含「重新對帳」鈕，D-125）與 `{TcsCard,DecompositionCard,CoverageList,WaiverInput,InnerLoopLinks,ScrStateBadge}.tsx` 與測試；`lib/domain/research.ts` 只增補 `coverageView()`、`scrBadge()`；**追認集合外兩檔** `tests/helpers/research.tsx`（只增 decomposition 選項與 GET 回放；§4 第 29 列「只增」）與 `lib/help/research-workspace.ts`（十一個欄位釋義；D-131）；`tests/e2e/research-build-front.mock.spec.ts`（新）；不得動 `ResearchWorkspaceView.tsx`、`schema.d.ts`、FE-D1 已定稿的型別 |
| PKG-FE-W | `AgentConsole/frontend/lib/api/schema.d.ts`（重產）、`lib/api/types.ts`（手寫型改引生成型）、`tests/e2e/research-docker.stack.spec.ts`（§4 第 26 列與 helper 合併）、`tests/e2e/README.md`、新 `tests/e2e/research-route-local.stack.spec.ts` 與 `research-p1-docker.stack.spec.ts` |
| 整合 P1 | `AgentConsole/engine-bridge/tests/test_research_int_p1.py`（若不歸 BR-D2）、`tests/fixtures/research/fake_gh/**`（沿用）、`AgentConsole/frontend/tests/e2e/README.md`（一句）、`AgentConsole/docs/06_quality/INT-ResearchToPRD-P1-*.md`（證據檔，主控落檔）；Docker 與本機模式實跑 |
| 根層名冊（主控；F-05） | `tools/tests/test_windowsapps_guard_bash_parity.py` 的名冊補列假 gh 夾具目錄（兩 commit、淨零行）——AT-961-23-1「禁區零差異」的明示例外：根層 shell 腳本目錄名冊 `_KNOWN_HOOK_DIRS` 補列 `AgentConsole/engine-bridge/tests/fixtures/research/fake_gh`（假 gh 替身的 POSIX 形態，非 git hook）——pre-push 的 `TestHookDirRosterIntegrity` 對新目錄出聲；commit fee50a4a、0af3a6bc（淨零行改法，不動 `_FROZEN_GUARD_LINES`）；非任何包的允許集合、只由主控修補 |

> **FIX 包**：修復棒的允許集合＝原包集合∪審查報告指名的檔（見〈提交順序與責任〉）。

---

## 6. RTM 連結確認

### 6.1 追溯
RTM 子表 `AgentConsole/docs/06_quality/RTM-ResearchToPRD-P1-20261107.md`（列數見 §1 計數；F 1、US 3、AC 與 AT 逐列）；`RTM.md` 的 §2.10 存根補一行 P1 引言（不計入 §2 總列數與 US 58）。每完成一項需求即回填四格（實作檔、自動測試、E2E 驗證、狀態），不得刪列、改號、合併列（`AgentConsole/CLAUDE.md` 鐵律 12）。

### 6.2 V 系列：實查檢核（主控、整合棒、掌舵者；**不是 AT**；證據文字逐字貼入 P1 證據檔與 RTM 的 E2E 驗證欄，未驗者如實標「未驗」）

- **V-R8**（AC-961-6；AC-R2P-13-4；PRD 出口 (j)）`gh auth status` 與 `GH_TOKEN` 傳遞行為的真機現查：本機 `gh` 在 Bridge 子行程環境（白名單重建後）下的認證路徑、`GH_TOKEN` 是否足以通過 `repo create`（以不建庫的唯讀探測，如 `gh auth status` 與 `gh api user`，不建立真庫；PKG-BR-D1 落證；ADR-003 D15、D16 的再開症狀入口）
- **V-H3**（AC-961-6；PRD 出口 (a)；D-92）掌舵者以 Private 測試庫真機一次軌道 B：主控於 RELEASE_READY 時以互動選項問「要不要現在用 Private 測試庫跑一次」，結果（含事後保留或移除）記為文字，不阻擋 RELEASE
- **V-D2**（AC-961-10、11；PRD 出口 (e)、(i)）本機模式全棧（backend 與 Bridge 同機、真 PG、拋棄式 clone、假 gh）端到端：分流成功→`:decompose`→覆蓋與豁免→簽核→未簽核啟動 409→PRD 摘要變更後 `decomposition_stale`；證據逐字貼入（Docker 內無 git 與 gh，故此路徑只能在本機模式）
- **V-D3**（AC-961-5；D-95）軌道 A 實測：本 monorepo 的 `git worktree add` 耗時、磁碟量與最長路徑；Windows 長路徑在 `core.longpaths` 開與不開兩種下各跑一次（PRD FR-R2P-12 邊界條件「Windows 長路徑與檔案鎖相容性於 P1 TCS 實測」）；結果寫回 ADR-003 D16 勘誤
- **V-D4**（AC-961-10；D-94）`:decompose` 同步呼叫的總耗時量測（INT 夾具與真引擎各一次；中位數大於 120 秒即列症狀，P2 候選改 stage run）
- **V-D1**（AC-961-22；AC-R2P-04-11、11-6）Docker 全棧 mock-only：AT-961-22-5 與 22-6 對真容器跑綠並貼輸出（容器只驗停用與缺項負控，真 git 副作用只在本機模式）
- **V-C1**（AC-961-24；AC-R2P-21-6）Architecture §5.4 檢查表逐項人讀對照（SCG-4 報告 §B）
- **掌舵者目視項**：RouteDrawer 兩卡、評估維度表、Public 警告、預演清單、失敗重試，與步驟 4 前半覆蓋矩陣在 1440、1000、600 寬度的觀感；結果記為文字，不充當 AT。
- **macOS 與 Linux 未驗項**：本鍵在 Windows 實作與驗證；macOS 未實跑的項目（含 POSIX 形態假 gh 夾具、symlink 子情境）一律標「未驗」，不得以 Windows 結果代表（NFR-R2P-10-3）。

---

---

## 7. 本檔採用的預設裁決（SD 依 PRD、ADR、契約與主控裁決 D-87～D-117、IFACE 與 PACKAGES 第二版判定；凡 PRD 與契約沒定到而 AT 需要的常數與形態都在此列；狀態「採納」＝主控裁決已定、「待裁決」＝SD 預設值、主控可推翻，推翻時走勘誤；「撤銷」列保留以維持編號）

| ⚖ | 狀態 | 裁決 | 來源或「本檔類推」 | WHY |
|----|------|------|-------------------|-----|
| ⚖P1-1 | 採納 D-94 | 拆解載體：Bridge `POST …:decompose`（同步 HTTP、非 stage run）＋console-api `POST …/decomposition`（觸發，OPERATOR 以上）與 `POST …/decomposition/signoff`（簽核，OPERATOR 以上）；簽核服務走既有 import／signoff 取得 `import_record_id` 後呼 Bridge `:decomposition-signoff`；契約補 API-RP-24、25 | PRD FR-R2P-14；契約 §1.1（原僅有 GET）；IFACE §1.4、§1.8；D-94、D-113 | 覆蓋對映是確定性的事，交程式碼；AutoClaude 零改動 |
| ⚖P1-2 | 採納 D-96、D-98 | capabilities 十三鍵不變；`scaffold_root`、`scaffold_templates`、`repo_writable` 取實值，`gh_cli.authenticated` 與 `git.version` 維持 `NOT-EVALUABLE`；gh 登入只在預演於 `create_github` 為真時探測。任務書所稱「五鍵」＝與分流停用有關的 `scaffold_root`、`scaffold_templates`、`repo_writable`、`gh_cli`、`git` | 契約 §2.1；IFACE §3.2；D-96、D-98 | 探針不起子行程的 P0 鎖不破；不新增欄位 |
| ⚖P1-3 | 採納 D-105 | `:route` 同步（200 或 502 `route_step_failed`），契約的 202 勘誤為 200；牆鐘 300 秒；console-api 讀逾時 330 秒 | 契約 §1.4、§2.2（202 與 502 同請求矛盾）；RISKS (b)-9 | 補償需要同請求內得知失敗 |
| ⚖P1-4 | 採納 D-106 | route 請求加 `owner`、`ci`、`docker_compose`、`project_name`，退役 `target_path`（Bridge 導出）；`GET …/route` 無列回 200 `null` | 契約 §1.2 `route.targetPath`；RISKS (b)-10 | 使用者輸入絕對路徑只增逃逸面 |
| ⚖P1-5 | 採納 D-100 | 落點目標清單為 Bridge 常數 `PLACEMENT_TARGETS`（四值）；PRD「ADMIN 維護」勘誤為「P1 固定四值」 | PRD :667、AC-R2P-12-3；V19 CHECK | DDL CHECK 四值已發佈 |
| ⚖P1-6 | 採納 D-118 | 游標與失敗標記細節的本檔類推：分流失敗 `flow_detail`＝失敗步驟名；SCR 序列 `BLOCKED` 時 `flow_detail` 為 `scr_blocked:<next_state>`；重試冪等判定取 `git branch --list` 與 `worktree list` 現查；中斷後步驟列標 `FAILED`（`stderr_tail` 為 `interrupted`） | D-77、D-105 體例；PRD AC-R2P-11-3、19-8 | 規格只定「停在第 3 步、可重試」與「BLOCKED 交人處置」，具體字串由本檔定 |
| ⚖P1-7 | 採納 D-112 | `COMPENSATED` 由 Bridge `:route-compensated` 寫（console-api 補償完呼叫），非 FAILED 列回 409 `route_conflict` | PRD :380、:660；RISKS (b)-16 | 研究表唯一寫入者＝Bridge |
| ⚖P1-8 | 採納 D-119 | 內環鍵文法 `^[a-z][a-z0-9-]{1,99}$`（A 為 `<module>-<slug>`、B 為 `<project_name>`）；`project_name` 正規式 `^[a-z][a-z0-9-]{1,61}$`，`repo_name` 預設取 `project_name`；worktree 根見 D-95 | D-119；IFACE §4.2 | 同時合 GitHub repo 名與 FSM 鍵文法 |
| ⚖P1-9 | 採納 D-118 | V19 的 `impl_fsm_actions` 內容形狀（陣列）DDL 不擋，由 Bridge 寫入器保證；本檔不要求新 CHECK | Architecture K.4 DDL 驗收段（未列） | Flyway 已發佈檔不改；V20 成本高 |
| ⚖P1-10 | 採納 D-118 | P1 的 gitops 允許表不含 P2 動詞（`tag -a`、`pr create`、`release create`）；P2 開工時再加 | ADR-003 D15、D16 | 最小白名單；判準精準 |
| ⚖P1-11 | 採納 D-118 | `tcs-draft` 前置不成立回 409 `fsm_state_conflict`，`details.unmet[]` 的項名（`route_not_succeeded`、`inner_key_not_adopted`、`decomposition_missing`）為本檔類推 | IFACE §1.3；D-110 | 契約只寫「需內環鍵已 Stage-1 採納」 |
| ⚖P1-12 | 採納 D-120 | `GET …/decomposition` 無拆解回 200 `null`；有效版＝已簽核且摘要相符的最新版（`status` 無 SUPERSEDED）；未覆蓋清單簽核回 422 `invalid_request` 的 `violations[{field: coverage, rule: uncovered_ac}]` | IFACE §3.1、§1.8；D-94、D-113 | 契約未定義 `DecompositionDto`；不另設 reason |
| ⚖P1-13 | 撤銷 | （撤銷；D-102）原判新增 reason `tcs_not_frozen`；改為既有 `fsm_state_conflict`；本列保留以維持編號 | D-102 | 不增 reason |
| ⚖P1-14 | 採納 D-104 | `scr_limit`：同 `research_id`、MINOR、`status` 為 OPEN、APPROVED、APPLIED 已有 2 筆即第 3 次 409；PRD「同一 Stage」勘誤為「同一研究專案（保守計）」 | PRD :799；ADR-017 D5 | Console 沒有內環 Stage 的穩定視圖 |
| ⚖P1-15 | 採納 D-121 | `fsm_flow_mapping` P1 增列只用 DB 游標值（route／ROUTING、route／FROZEN、build／ROUTED、build／TCS_DRAFTING、build／TCS_PENDING、studio／SCR_OPEN）；`BUILD_READY`、`PAUSED` 為衍生、不入對映；`TCS_PENDING × Stage-2 已凍結` 為待校正而非 drift | D-121；D-125 | 對帳比 DB 與 FSM，衍生值沒有 DB 面 |
| ⚖P1-16 | 採納 D-118 | records/audit 的 V19 口徑：R7＝`research_route_decisions`、R8＝`research_decompositions`、R10＝視圖、R11＝`research_deliveries`、R12＝`research_scr`；完成分流與簽核的專案 `missing` 恰 `R11` | 契約 §1.4 API-RP-19（「V19 落地後的口徑以勘誤補列」） | 契約明示留待補列 |
| ⚖P1-17 | 採納 D-118 | 步驟 4 前半面板在 `SCR_OPEN` 時停用觸發拆解、簽核、草擬並顯示「規格變更中」；SCR 發起鈕與橫幅屬 P2 | PRD 頁面 4 狀態（「SCR 開啟＝橫幅＋啟動／恢復停用」） | 與後端 409 `scr_open` 一致；看板屬 P2 |
| ⚖P1-18 | 採納 D-118 | 範本內的 Python 檔一律以 `.tmpl` 後綴存放、展開時去後綴，`pyproject.toml` package-data 納入範本目錄 | `test_research_ast_locks.py:157-159` 與 `test_research_capability.py` 掃 `app/` 全部 `.py`；PACKAGES 第二版範本清單含 `app/main.py`、`tests/test_smoke.py` | 否則範本檔被 AST 鎖解析並要求 `CAPABILITY` 登記（含 `{{…}}` 佔位會語法錯） |
| ⚖P1-19 | 採納 D-118 | 軌道 B 步驟序取 IFACE §4.3（SCAFFOLD_FILES、COPY_WORKSPACE、GIT_INIT、GIT_COMMIT、GH_REPO_CREATE），與 PRD FR-R2P-13 敘述序（複製→git init→產生檔→commit）不同 | PRD FR-R2P-13 描述；IFACE §4.3 | 產生檔先於 git init 使 `.gitignore` 先就位；結果等價 |
| ⚖P1-20 | 採納 D-122 | 預演缺項項名＝`git`、`gh`、`repo_writable`、`scaffold_root`（未設根）、`scaffold_templates`（目錄空）、`worktree_root`、`gh_auth`；`scaffold_root` 與 `scaffold_templates` 分開列 | D-122 | 兩種缺項修法不同 |
| ⚖P1-21 | 採納 D-118、D-128 | P0 未結「BLOCKED_DB 游標校正時機」：oracle 取 P0 原文（`_chain` 遇 DbBlocked 不排 FAILED、游標 `flow_status` 不重新衍生、BLOCKED_DB run 的游標要等下次 stage 動作才校正；PKG-BR-C 交卷、TCS-P0 AT-960-2-5、RTM-P0）；P1 校正時點＝outbox 重放完成的同一交易重新衍生游標 | RISKS (c)；D-128 | P0 行為不改，P1 只補重放後校正 |
| ⚖P1-22 | 採納 D-119 | 軌道 A 的 PRD 發佈路徑＝`<子專案根>/docs/01_requirements/<slug>_PRD.md`（slug 原樣）；軌道 B 不另發佈（採納 `my-project/<slug>/01_specs/PRD-v1.0.0.md`）；落點 stub 檔名依 D-101 | D-119；D-101 | 單一確定性轉換、零歧義 |
| ⚖P1-23 | 撤銷 | （撤銷；IFACE 第二版）原判簽核請求缺 `waivers`；IFACE §1.8 已含選填 `waivers[{ac, reason}]`；本列保留以維持編號 | IFACE §1.8 | — |
| ⚖P1-24 | 採納 D-118 | operationId 定案：`previewResearchRoute`、`routeResearchProject`、`getResearchRoute`、`openResearchScr`、`listResearchScr`、`applyResearchScr`、`getResearchDecomposition`、`triggerResearchDecomposition`、`signoffResearchDecomposition` | D-118 | 函式名須與前端端點函式一一對應 |
| ⚖P1-25 | 採納 D-118 | R-2 尾巴四個 reason（`compile_failed`、`sdd_cli_failed`、`fsm_state_unreadable`、`invalid_request`）併入四方鎖，總數 35；`invalid_request` 納入後改 `RESEARCH_` 前綴常數；若主控判不併入，AT-961-15-4 的 `P0_TAIL_REASONS` 整段移除、總數回 31 | SCG-4 二審 R-2；RISKS (c) | 避免 `P0_REASONS` 命名再改兩次 |
| ⚖P1-26 | 採納 D-123 | R-1（allowlist 條目 404 訊息）歸 API-P1：`ResearchBridgeErrors.java:50` 依 details 或路徑區分文案，reason 仍 `research_not_found`，Bridge 不動 | SCG-4 二審 R-1；D-123 | 文字住 console-api，一包改完 |
| ⚖P1-27 | 採納 D-118、D-124 | D-45「P0／P1 不呼叫內環 `gate`」與 PRD AC-R2P-19-8 的 SCR 序列（`gate PR_REVIEW FAIL`、`gate RTM_VERIFY FAIL`、`gate RELEASE_READY FAIL`）衝突：本檔取 AC-19-8（SCR 序列為 D-45 的明示例外；`POST …/gates` 的登錄用途仍為 P2）；AT-961-7-E-2 的「採納序列 gate 為 0 次」仍成立 | D-45；PRD AC-R2P-19-8；ADR-017 附錄 A | D-45 針對 SCG 登錄端點，SCR 序列是另一條路 |
| ⚖P1-28 | 採納 D-97 | Stage-2 的 `transition --to HUMAN_PENDING` 用第二個理由前綴 `tcs gate`（限內環鍵、現態 SCG_VALIDATION、已有 Stage-1 凍結），動詞集合不變 | ADR-017 D2；IFACE §5.2；RISKS Q-4 | 避免讓 `decision_trace` 說謊 |
| ⚖P1-29 | 採納 D-102 | 執行前置守衛三個 409（`scr_open`、`decomposition_stale`、TCS 未凍結＝`fsm_state_conflict`）住既有啟動服務、只對研究專案生效；PRD AC-R2P-14-7「凍結前內環 run 啟動回 409」由它承擔 | PRD AC-R2P-14-4、14-5、14-7；D-102 | FR-R2P-15-2 禁第二套執行控制 |
| ⚖P1-30 | 採納 D-103 | SCR：console-api 先呼既有 stop 用例再呼 `:scr`；MINOR 於 `:approve-baseline` 偵測 OPEN 即以 `Gate-0-SCR<k>` 凍結並同請求套用；失敗留 `APPROVED`、`:scr-apply` 重試（console-api 端點僅 ADMIN）；`versionBump` 加入 `:approve-baseline` 選填欄 | PRD FR-R2P-19；契約 API-RP-12；RISKS (b)-8 | 核准即套用才沒有空窗 |
| ⚖P1-31 | 採納 D-109、D-110 | TCS 草擬：agent 只寫 `03_execution/tcs_draft.md`，Bridge 確定性驗證即「SCG 預檢」；先拆解、後 `tcs-draft`（前置為已有拆解列）；`not_implemented` reason 保留（D-111） | PRD FR-R2P-14；D-74 | agent 工具權限只到工作區 |
| ⚖P1-32 | 採納 D-115 (b)-1～16 | RISKS (b) 十六處不一致全部照其「建議勘誤方向」：(1) 契約補拆解端點；(2)(3) R7、R8 以 artifacts 承載並以 sha256 對帳；(4) 單一寫入時點；(5) 固定四值；(6) 軌道 B 版面；(7) AC-19-1 內環鍵不回 IMPLEMENTATION；(8) `versionBump`；(9) `route` 同步；(10) 退役 `targetPath`；(11) SCR 契約加 `reasonClass`；(12) 補 `DecompositionDto`；(13) gitops 白名單補洞；(14) 談判動詞註記；(15) `:approve-baseline` 游標在 SCR 時依 19-4；(16) `COMPENSATED` 寫入者 | RISKS (b)；D-115 | 不原地改凍結檔，RELEASE_READY 一併 refreeze（§4.4） |
| ⚖P1-33 | 採納 D-117 | `target_not_empty` 的 `details.path` 只回相對 `BRIDGE_SCAFFOLD_ROOT` 的路徑；軌道 B 副本含 `00_research/raw/**`、以範本 `.gitignore` 排除入版控（PRD AC-R2P-13-2 與 13-5 措辭一致化進勘誤） | D-117；PRD :693、:696 | 不洩絕對路徑；兩 AC 同時成立 |
| ⚖P1-34 | 採納 D-116 | P1 不需 V20：`research_artifacts.kind` 已含 `ROUTE_DECISION`、`TASK_DECOMPOSITION`、`TCS`；`research_events.event_type` 無 CHECK；`flow_phase` CHECK 已含 `ROUTING`、`ROUTED`、`TCS_DRAFTING`、`TCS_PENDING`、`SCR_OPEN`；`IMPORTED` 拆解狀態 P1 不使用 | Architecture K.4；V16 | Flyway 已發佈檔不改 |
| ⚖P1-35 | 採納 D-118 | AT 數與 AT 切分為 SD 判斷：同一 AC 內數字序與 E 序各 ≤9；契約級 AC 比 AC-R2P 粗（沿 P0） | ADR-XPLAT-016 §8.1 | 編譯器對 AT 文法的限制 |
| ⚖P1-38 | 採納 D-126 | 基線採納住新模組 `app/research/adopt.py`（`adopt.adopt_baseline`）；AST 鎖 C2 白名單加該檔，限內環鍵與 `--stage Stage-1`，紅綠夾具各一；全文統一此名（不再放在 route 模組內） | D-126；`test_research_ast_locks.py:131-136` | C2 原只准 HTTP 處理函式呼叫 `spec_frozen`，採納需在 Bridge 內呼叫 |
| ⚖P1-39 | 採納 D-127 | AT-961-24-1 的判定改為入庫可跑的 shell 一行式（PowerShell 與 bash 並列，Select-String／grep -c 數 TCS 與 RTM 的定義列，期望值寫死），不引用 scratchpad 自檢腳本 | D-127；QA F-07 | 自檢腳本不入庫、他機無法重現 |
| ⚖P1-37 | 採納 D-125 | TCS 經既有 `:freeze` 凍結後游標校正三段機制：(1) 讀端衍生（`ResearchFlowPolicy.effective` 於 `TCS_PENDING` 且 `FsmView.stage2Frozen` 回 `build／BUILD_READY／IDLE`，API-P1）；(2) Bridge `:reconcile` 同交易校正為 `build／ROUTED／IDLE` 並記 `research.step`（`reason=tcs_frozen_correction`，BR-D2）；(3) 既有 SDD freeze 服務成功後綁研究專案時呼 `:reconcile`（API-P1），UI 步驟 4 面板提供「重新對帳」（FE-D2） | D-125；ADR-003 D5（游標是投影） | 既有 `:freeze` 不認研究游標、改 `routers/sdd.py` 違最小侵入；校正走研究面唯一寫入者 |
| ⚖P1-36 | 採納 D-92 | 掌舵者 Private 測試庫真機（真 GitHub 建庫）列為 V-H3，不阻擋 RELEASE；代驗面以假 gh 涵蓋 AC-R2P-13-2、13-4、13-5 | PRD §8.1 P1 出口 (a)；D-92 | 真機建庫有對外副作用與 token，必須真人決定 |

---

## 📋 SCG-4 通過標準

1. §3 全部 AT 綠（Bridge pytest 在 `BRIDGE_TEST_DSN` 與 `SDD_ROOT` 皆在場下 0 skipped、backend `gradlew clean build` 為 BUILD SUCCESSFUL 且 JaCoCo 不低於 80%、frontend vitest 覆蓋率不低於 70% 且 `tsc`、`lint`、`build` rc 0；Docker E2E 對全棧綠；各 AT 的輸出逐字貼入證據）。
2. §4 各列同步只改預期值、零刪斷言（例外列依 §4 開頭明示）；§4.4 凍結文件勘誤各補一列並於 RELEASE_READY 一併 refreeze。
3. §5.7 各包集合外零差異、禁區零差異（AT-961-23-1）；不新增 `os.replace`、`rename`、`move` 站點（AT-961-23-2）；不新增 hook 與守衛（AT-961-23-3）。
4. §1.2 的 P1 AC-R2P 皆有 AT 或 V 的正向證據；§1.3 的 P2 條目不得被算作已覆蓋。
5. V 系列（§6.2）：V-R8、V-D1、V-D2、V-D3、V-D4、V-C1 皆有文字證據或如實標「未驗」；V-H3 為掌舵者真機（構造情境不能充當，事後保留或移除由掌舵者決定）。
6. 文件連動全部落地（AT-961-24-1）；RTM 子表每列回填；`AgentConsole/CLAUDE.md` 不超過 200 行、`README.md` 不超過 80 行。
7. PRD §8.1 P1 出口 (a) 至 (k) 逐項有證據（§1.4 對照表）。

## 勘誤（凍結後的訂正；內文已就地訂正、被訂正的原文逐字保留於下表；走 `spec-refreeze`）

> 本表於 Stage-2 凍結時為空；凍結後的訂正於 RELEASE_READY 批次一併寫入並 refreeze（日期欄只寫月-日、不寫四位數年份，原因同 TCS-P0 勘誤表的註解：避免行內數字觸發基線站點掃描）。

| 編號 | 日期 | 位置 | 原文 | 訂正 | 原因與證據 |
|------|------|------|------|------|------------|
| E-1 | 11-07 | §5.7 PKG-BR-D1 列 | 原文：「…不得動 `sdd_cli.py`、`fsm_ops.py`、`routers/research.py`、`compile/*`」 | 已就地訂正：加 `app/sdd_cli.py`、`app/research/fsm_ops.py` 的 inner-create 擴充（主控落地）與 `engine-bridge/README.md` | D-129（BR-D1 交卷 B1） |
| E-2 | 11-07 | §5.7 PKG-BR-D2 列 | 原文：「`app/routers/research.py`（移除 tcs-draft 501、`:approve-baseline` 的 open-SCR 分支與 `versionBump`、`reap_route_orphans` 接線）」 | 已就地訂正：追認 `tcs_unmet` 助手與 `TCS_*` 常數、檔尾 `include_router(research_scr)`、`reconcile_at_route` 助手 | D-134(1)(2) |
| E-3 | 11-07 | §5.7 PKG-FE-D1 列 | 原文：集合不含 `lib/help/states.ts`、`lib/nav/research-nav.test.ts` | 已就地訂正：追認兩檔（型別與詞彙改動的必然連動） | D-130 |
| E-4 | 11-07 | §5.7 PKG-FE-D2 列 | 原文：集合不含 `tests/helpers/research.tsx`、`lib/help/research-workspace.ts` | 已就地訂正：追認兩檔 | D-131 |
| E-5 | 11-07 | §5.7 PKG-API-P1 列 | 原文：集合不含 V20、`ConfigCatalog`、設定類 IT 與 `research_pg_support.py` | 已就地訂正（§5.7）：補列（`research.github_token` 種子；設定鍵 50→51；版本清單加 `"20"`；`LAST_VERSION` 加 20）；FRD-lite After 第 1 點的「P1 不需 V20」另訂正為「V20 只種一列設定、不加表」（僅登記於本表，不改 FRD-lite 條文） | D-132、D-98 訂正 |
| E-6 | 11-07 | §5.7 整合 P1 列、新增根層名冊列 | 原文：整合列無 `tests/e2e/README.md` 與 `INT-*.md`；無根層名冊 | 已就地訂正：整合列補兩項；新增「根層名冊（主控）」列追認 `tools/tests/test_windowsapps_guard_bash_parity.py` 補列（AT-961-23-1 的明示例外） | SCG-4 F-05 |
| E-7 | 11-07 | AT-961-13-3（共同序列） | 原文：「先 `gate RTM_VERIFY FAIL`、RELEASE_READY：先 `gate RELEASE_READY FAIL`…回傳 IMPLEMENTATION 則續跑」（共同序列未載現態前置） | 訂正：退回 IMPLEMENTATION 後與其他起跑現態相同，`spec-refreeze` 之前須再 `transition --to SPEC_AUDIT`（框架 `spec-refreeze` 只准 SPEC_AUDIT／RELEASE_READY／RELEASE 現態，實跑 rc=3）；IFACE §5.3 與 ADR-XPLAT-017 附錄 A 同步 | D-134(1) |
| E-8 | 11-07 | AT-961-13-8、13-E-2、13-E-3（回報語意） | 原文：發佈失敗或 FSM 非 0 步驟「回報 `BLOCKED`」 | 訂正：步驟出錯（發佈失敗、FSM 動詞非 0）＝`FAILED`，可由 `:scr-apply` 續做；`gate` 回傳 `next_state` 不是 IMPLEMENTATION（含 ESCALATION）＝`BLOCKED`，只有人能解、不重試；13-E-3 的 `BLOCKED` 回 200 僅指後者 | D-134(2) |
| E-9 | 11-07 | AT-961-20-3（函式簽名） | 原文：純函式 `flow_fsm_mapping_ok(fsm_state, flow_step, flow_phase, stage2_frozen)` 回真假與第三態 | 訂正：新增三態函式 `flow_fsm_mapping_verdict(…, stage2_frozen=)`；舊 `flow_fsm_mapping_ok` 簽名不動（P0 的 `AT-960-21-2` 零改動） | D-134(3) |
| E-10 | 11-07 | AT-961-9-3（檔名變體） | 原文：「檔名不合 `_freeze` 的 `_TCS_NAME`」變體 | 訂正：檔名變體只做函式級驗證（`tcs_schema` 的檔名規則），不另走整條 stage 路徑 | D-134(4) |
| E-11 | 11-07 | AT-961-12-2（affected_sections 形態） | 原文：「`affected_sections` 含不存在章節、不存在 AC」 | 訂正：`affected_sections` 接受 `5.2`、`§5.2`、`AC-…`、`5.2/AC-…` 四種寫法，未知項逐筆 `affected_unknown` | D-134(5) 第 9 條 |
| E-12 | 11-07 | AT-961-13-E-1（閘數） | 原文：「四個閘 `current_count` 皆為 0」 | 訂正：`RETRY_GATES` 三閘（SCG_VALIDATION、PR_REVIEW、RTM_VERIFY）皆為 0 | D-143(1) |
| E-13 | 11-07 | AT-961-4-E-1（Then 段） | 原文：「Then 阻塞期間…；P1 校正時點：outbox 重放完成的同一資料庫交易內…重新衍生游標」「路由列 SUCCEEDED、游標 build／ROUTED／IDLE」 | 訂正：DB 阻塞時分流中止、路由列留 RUNNING、游標 `route／ROUTING／RUNNING`（不是 BLOCKED_DB）；「路由列 SUCCEEDED、游標 build／ROUTED／IDLE」只在 `route.finish` 之後才斷線的晚斷線案成立（AT 已分兩案） | D-143(2)、D-128 |
| E-14 | 11-07 | AT-961-10-6（後半） | 原文：「`tasks_count` 等於 JSON 內 task 數且等於已簽核版本落成的正式 tasks 數」（實作原缺 `imported_tasks_count`） | 訂正：不勘誤掉、修到正解——簽核本文加 `imported_tasks_count`（≥0 整數，缺／型別錯／負數／bool／浮點＝422 `invalid_request` 違規 `imported_tasks_count_invalid`），Bridge 記進簽核版 artifact 與回應，AT 斷言 `tasks_count == imported_tasks_count`；不相等的處置＝由對帳 `task_decomposition` 項回報（P2 承接）；契約 `:decomposition-signoff` 請求／回應與 violations 規則表同步 | D-143(3)、D-146（FIX-P1，commit 92d50ccd） |
| E-15 | 11-07 | AT-961-6-E-1（尾句） | 原文：「`BRIDGE_SCAFFOLD_ROOT` 自動併入 `BRIDGE_ALLOWED_PATH_ROOTS`（ADR-003 D8），啟動時於 `/health/deep` 揭露」 | 訂正：改由 `capabilities.scaffold_root` 揭露（`/health/deep` 八鍵與 capabilities 十三鍵鎖不動） | D-134(4) |
| E-16 | 11-07 | AT-961-6-E-2（編碼形態） | 原文：「token 以 URL 編碼形式出現」 | 訂正：編碼形態含不保留字元被編碼（`%5F`／`%5f`）與被空白切開，`gitops.redact` 以逐字元「字面或 `%XX`（大小寫皆可）」且可被空白切開的樣式去敏（一審 F-10：`_percent_encode` 正規形式不編 `_`，`%5F` 形態真外洩） | D-146、SCG-4 F-10（FIX-P1，commit 92d50ccd） |
| E-17 | 11-07 | AT-961-17-4、17-5、19-2、16-5（字面） | 原文：17-4「`project_name` 與 `repo_name` 取 `^[a-z][a-z0-9-]{1,38}$`」；17-5「`actions[]`（含 `external: true`…）」；19-2「第 3 步說明含…OPERATOR 可預演、僅 ADMIN 可確認…」；16-5「文案取 `lib/help/research-workspace.ts` 登記值」 | 訂正：17-4 `project_name` 取 `{1,61}`、`repo_name` 取 `{1,38}`（D-119）；17-5 欄位名統一 `touchesExternal`（`external` 為別名）；19-2 該句放 step、其餘放欄位釋義（step 一句 ≤60 字）；16-5 文案取單一登記處 `lib/domain/research.ts::ROUTE_DISABLED_TEXT` | D-130(3)(4)(6)(7) |
| E-18 | 11-07 | AT-961-18-7（字面）與 `tcs_invalid` 載體 | 原文：18-7「拆解與 FSM 視圖請求失敗」 | 訂正：「專案詳情與拆解請求失敗」；`tcs_invalid` 載體＝`flow_detail` 寫 `tcs_invalid: <缺項文字>`、另發 `research.alert{kind:tcs_invalid}`（AT-961-9-3 的細項寫法同步） | D-131(2)(3)、D-134(5) |
| E-19 | 11-07 | AT-961-11-2、11-E-1、14-8、`POST …/scr` 回應碼 | 原文：11-2「憑證無 subject（空字串）400」；11-E-1「allowlist 外 422 `sanitization_failed`…」；14-8 逾時表；`POST …/scr` 的回應碼字面與實作不一致 | 訂正：11-2 空 subject＝401（JWT 層）；11-E-1 `executionPath` 非絕對或含 `..` 段＝422 `invalid_request`、`:route` 零請求；14-8 逾時表測試住 `BridgeHttpAdapterResearchTest`；`POST …/scr` 一律 202；拆解 artifact 內容須含 `coverage{total,covered,uncovered[]}`；`failureStep` 透傳 snake_case `failure_step`；簽核冪等（匯入成功而 Bridge 失敗後重試，匯入記錄與目標任務數不增） | D-133 |
| E-20 | 11-07 | AT-961-22-5、22-6（真棧） | 原文：22-5 預演回 `route_unsupported_in_deployment`；22-6「build 顯示拆解面板空狀態與停用的草擬」 | 訂正：軌道 B 在容器內可先被欄位驗證擋成 `invalid_request`（範本清單空），22-5 接受兩種 reason 之一；22-6 真棧半改「超前導回＋拆解／SCR 讀端點空值＋tcs-draft 409」（mock-only 到不了 build，面板呈現由 mock spec 覆蓋） | D-135 |
| E-21 | 11-07 | AT-961-12-E-2（新列） | 原文：（無此條）→ 訂正：新增 AT-961-12-E-2（open_minor 外環轉態失敗補償：SCR 標 REJECTED、游標還原、槽位釋出；測試 `test_research_scr.py::test_AT_961_12_E_2_outer_transition_failure_marks_the_scr_rejected_and_restores_the_cursor`）；同步 §1.2、§1.5、§3、檔頭計數（AT 209→210、負控 43→44）、AT-961-24-1 期望值（210／239）與 RTM-P1 增一列（238→239） |  | SCG-4 F-09、D-146 |
| E-22 | 11-07 | RTM 對照（F-06） | 原文：AT-961-9-E-1、9-E-2、13-9、19-3、19-6、20-E-1、22-8、23-E-1 及 23-x、24-1 於 repo 無 `AT_961_` 命名測試 | 訂正：RTM-P1 各列「自動測試」欄已指向實際覆蓋的測試（9-E-1←9-4 與 9-3；9-E-2 承接半←10-7、失敗後再啟動走完成功路徑由 9-3 加 9-4 合覆蓋；13-9←13-1；19-3←stateKeys 全域掃描；19-6←design-rules 全域掃描；20-E-1←20-1；22-8←P0 既有 Docker 路徑；23-E-1←整合檔夾具設計；23-x、24-1 為 Gate 指令）；TCS 條文不改 | SCG-4 F-06（RTM 回填，commit efa7c041） |
| E-23 | 11-07 | §4 修復棒 commit 登記 | 原文：（無） | 訂正：登記 SCG-4 修復三筆——FIX＝92d50ccd（F-01、F-02、F-03、F-04、F-09、F-10、D-135 收口）；FIX2＝b8564085（F-11 outbox 晚綁定校正、F-12 STALE 覆蓋補測試）；FIX3＝c0a2a0b7（F-13 gitops.redact 編碼形態兩子特性斷言、F-14 補測試；PKG-FIX3-P1） | D-146、SCG-4 二審 |
| E-24 | 11-08 | AT-961-18-5、18-6（Then 字面） | 原文：18-5「…看板、自癒與終端屬 P2，本面板不渲染」；18-6「…發起 SCR 的按鈕屬 P2、不在本面板（⚖P1-17）」 | 訂正：P2 起看板、SCR 鈕與橫幅接進同一面板——18-5 改「內環鍵未採納時不渲染看板」（並加 AT-962-25-3a）；18-6 改「有發起 SCR 的鈕，規格變更中停用並顯示登記文案」；SCR 橫幅整併為單一 `scr-banner`（`BuildFrontPanel` 的 P1 位置渲染 `ScrBanner`、根元素保留 `data-testid="scr-banner"`，文案為 P1 斷言與 AT-962-15-5 的超集）；斷言只擴不縮 | D-155（FE-P2A，commit 28d36d6f）；連動 TCS-P2 §4.6 第 48 列 |
| E-25 | 11-08 | AT-961-20-E-4（Then 字面） | 原文：「…`drift`：顯示漂移警示橫幅（沿 P0 文案）…」（橫幅位於步驟 4 面板內的 `build-drift-banner`） | 訂正：依 D-131(6) 兩處漂移橫幅整併，面板內的 `build-drift-banner` 刪除、歸工作區單一 `drift-banner`；本 AT 對 `pending_correction` 與 `NOT_EVALUABLE` 的斷言不變，`drift` 的橫幅斷言改掛工作區 | D-155、D-131(6)；PKG-FE-P2A |
| E-26 | 11-08 | P0 `AT_960_19_6`（連動，不改 TCS-P0 條文） | 原文：P0 工作區按鈕停用鎖 | 訂正：鎖只增不減——P2 新增的 `tag-create` 等操作鈕納入「VIEWER 下停用」清單；「開啟本地專案」複製鈕在 VIEWER 下**不渲染**（只顯示可選取的路徑文字），P0 `AT_960_19_6` 的既有斷言一字不動 | D-150#1、D-157（FE-P2B，commit 10daf683） |