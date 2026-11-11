# Test Contract Specification — 研究來源單一化（Console 半：追蹤來源表與 Flyway V24／V25、Bridge 追蹤來源端點與登記快照、console-api 追蹤來源端點與同步／同步狀態端點、稽核 JSON 新 kind `src-registry`、研究來源設定對話框的追蹤來源區與同步、自我進化頁說明、E2E 與無障礙）
# 測試契約規格文件（增量變更；FRD-lite 併入檔頭；根層半另有 `TCS-SelfImproving-P6-20261110.md`）

**文件類型**: Test Contract Specification (TCS)
**SDD Gate**: SCG-4 PR Review Gate（RG-TEST 為補充閘）
**使用時機**: 已凍結系統（AgentConsole；上位文件含 ResearchToPRD 三期的 PRD／契約／TCS 與 SelfImproving P2b／P4 的契約與 TCS）的單一 Feature（研究來源單一化的 Console 半）；FRD-lite 與 TCS 同檔
**存放位置**: `AgentConsole/docs/03_testing/contracts/TCS-ResearchRegistry-20261110.md`（相對 monorepo 根；`spec-frozen --root` 取 monorepo 根，因上位文件含根層 PRD）
**spec-format-version**: 1.0
**scenario**: brownfield

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **Feature ID** | F-940 |
| **Feature 名稱** | 研究來源單一化（Console 半）——`console.research_watch_sources`（Flyway V24：表、擴充通用守衛、17 列種子、4 個 FETCH 網域種子）、`si_console_writes.kind` 放寬為六值（V25）、Bridge `GET／POST／PATCH /research/watch-sources` 與 `GET /research/registry`（登記快照、正規化規則、黃金檔 G-R1 與根層附錄 B golden）、Bridge `POST /si/registry:sync`、console-api `GET／POST／PATCH /api/v1/research/watch-sources`（API-RP-29）與 `GET／POST /api/v1/si/research-registry[/sync]`（API-SI-14／15；閘門序、冪等、補償）、稽核 JSON kind `src-registry`、對帳讀面新 kind、研究來源設定對話框的「自我進化追蹤來源」區與同步狀態、自我進化頁一行說明、每頁說明、Docker 全棧 E2E 與無障礙 |
| **User Story** | US-R2P-24（PRD FR-R2P-24；本檔 FRD-lite 沿用 US-940 對映） |
| **建立日期** | 2026-11-10 |
| **輸入快照** | HEAD＝`b562d063d7017323e8bde1b94ffb3bc6afc900d3`（`git rev-parse HEAD` 現查）；上位檔 digest 見〈增量追溯表〉，**由主控於凍結前以 `Get-FileHash -Algorithm SHA256` 重算**（本欄值為 SD 棒 2026-11-10 現算，供對照） |
| **QA 負責人** | 本鍵 SCG-4 QA 棒（獨立審查者；規格作者＝本 TCS 的 SD 棒，實作者＝鍵 `agentconsole-research-registry` 的三個開發 agent〔PKG-BE、PKG-BR、PKG-FE〕，三方不同） |
| **FSM 功能鍵** | `agentconsole-research-registry`（**依賴根層鍵 `monorepo-si-p6-registry-backtest` 的規格已凍結**〔事件欄位、鏡像檔、CLI 入帳動詞、`consoleaudit` 新 kind 的位元組權威〕；黃金檔 G-S1（根層產出，Console 只複製並以 Java 重新產生比對）與真入帳 V 項須待根層實作完成。共享附錄 A～D 以根層 TCS 為唯一本文（§5.1）。一律從 monorepo 根啟動：`python AISDLC_SDD/scripts/sdd_env.py --sub agentconsole --slug research-registry`） |
| **SCG Gate** | SCG-4 □ 待審 |

---

## 增量變更專用：FRD-lite 與〈增量追溯表〉

> 適用 `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`〈增量（delta）條款〉：變更限於已凍結系統的單一 Feature。**凍結檔不得再改**：發現需修訂處一律寫在 §7 的清單，走掌舵者 T1／SPEC_REGRESSION_CHECK。**與根層 TCS 的接縫**（`docs/03_testing/contracts/TCS-SelfImproving-P6-20261110.md`，下稱「根層 TCS」）：`research.registry` 事件欄位、鏡像檔 `research_registry.json` 的寫入與驗證、CLI 入帳動詞與 `_ingest_argv` 對應、`consoleaudit.py` 對 `src-registry` 的 body 判準與位元組權威、SI 抓取預檢與 `research_fetch_max`，**一律引根層 TCS 的條文編號、不在本檔複寫判準**；本檔只釘 Console 側（HTTP 形狀、閘門序、前端呈現、Bridge 落檔、Flyway、快照確定性）。契約文件＝`AgentConsole/docs/02_architecture/API_Contract_ResearchToPRD.md` §5A（本鍵新增；v1.0.0-rc3＋增量 v0.1）。

### FRD-lite

**現況與變更（Before／After；brownfield；現況於撰寫時現查，每項附座標）**

- Before：(1) SI 的研究來源只存在 git 檔 `docs/06_quality/SelfImproving_Protocol/research_sources.json`（網址層 15 筆，9 現役、6 retired；`id`／`url`／`kind`／`extract`／`added_by`／`retired`），與 Console「研究來源設定」無關；(2) Console 的研究來源設定只有網域層：`console.research_allowlist_entries`（`V17__research_evidence.sql:103-123`；受控更新只放行 `enabled`／`disabled_by`／`disabled_at`）＋部署基底 `BRIDGE_RESEARCH_FETCH_ALLOWLIST`，UI 住 `components/domain/research/AllowlistDialog.tsx`（由 `app/research/page.tsx:10` 以 `extraActions` 掛入）；(3) 通用守衛 `console.research_controlled_update_guard()`（`V16__research_core.sql:57-92`）的允許清單有九條；(4) `console.si_console_writes.kind` 的 CHECK 為五值（`V23__si_console_writes_kind_sched.sql:19-21`），欄寬 `VARCHAR(12)`（`V13__si_console_writes.sql:15`）；(5) `SiWriteKind` 五值（`SiWriteKind.java:10-16`）；Bridge 的 SI 落檔路由四個（`routers/si.py:233-274`）；(6) `SiReconcileService.scan()` 只認 `dec`／`obs.add`／`obs.close`／`sched.set`／`run.open`／`sched.skip`（`SiReconcileService.java:124-132`）；(7) 前端不持有 `console.si.deciders` 名單，寫入帳號是否被允許由 backend 回 403 `si_write_forbidden` 判（`lib/api/endpoints.ts:615` 註解、`lib/domain/si.ts:53-54`）。
- After：(1) 追蹤來源住 `console.research_watch_sources`（V24；種子 17 列），SI 讀由 Console 簽章同步而來的鏡像檔，不再讀 `research_sources.json`；(2) 研究來源設定對話框加追蹤來源區、同步狀態與同步鈕（W-R8）；(3) V24 以 `CREATE OR REPLACE` 擴充既有通用守衛增第十條允許清單（W-R1）；(4) V25 把 kind CHECK 放寬為六值（W-R2）；(5) Bridge 加 `GET／POST／PATCH /research/watch-sources`、`GET /research/registry`（W-R3、W-R4）與 SI 落檔路由 `POST /si/registry:sync`（W-R6）；console-api 加 API-RP-29、API-SI-14、API-SI-15（W-R5～W-R7）；(6) 對帳掃描加事件種類 `research.registry`→`src-registry`（W-R7）；(7) 同步被 403 時前端依既有做法顯示「此帳號不在自我進化寫入名單，未同步」（W-R8），不新增名單機制；(8) 自我進化頁加一行統一管理說明（W-R9）。
- **非目標**：不改 R2P 既有 allowlist 三個端點的行為與 Bridge 請求數；不讓研究 run 使用追蹤來源；不改 `check_research_url` 與研究抓取層；不新增 ADMIN matcher 給同步端點（沿 `POST /api/v1/si/**`）；不改 `si_console_writes_guard()` 觸發器與欄寬；不改 Architecture／ADR（最小文件集，見 §7.1 第 10 項）；不做任何刪除 UI（追蹤來源只增不刪）；不在 Console 持有 `research_fetch_max` 常數；不做 force 同步；Console 不寫 SI 帳本。

**AC 編號規則**

1. **編譯文法**：AC 為 `AC-[\d\-]+`、AT 為 `AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*` 且 AT 前兩段數字＝所屬 AC（ADR-XPLAT-016 §8.1）。
2. **對映**：AC 取 `AC-965-1`～`AC-965-10`，與 PRD `AC-R2P-24-1`～`AC-R2P-24-10` 逐一對映（`AC-965-k` ↔ `AC-R2P-24-k`）；本檔不自增 AC。
3. **AT 命名**：`AT-<AC 數字 id>-<序>`；負控與邊界 `AT-<AC 數字 id>-E-<序>`；測試名含其底線形（`AT-965-6-3`→`AT_965_6_3`；Java 方法名以底線形開頭加駝峰敘述）。每個 AC 內數字序與 E 序各不超過 9，使 `-t`、`--tests`、`-k`、`-g` 的子字串比對不會誤收其他 AT。
4. **計數**：AC 10 個、AT 74 個（其中編號含 `E` 的負控與邊界 9 個；分佈見 §3 末）。〔勘誤 E-14：73→74，新增 AT-965-10-4〕

**FRD-lite 表**（第一欄為 US ID；AC 的完整 Given／When／Then 住 PRD FR-R2P-24 與 §2 各 AT，本表給摘要）

| US ID | User Story | AC ID | AC（Given／When／Then 摘要） |
|-------|------------|-------|-----------------------|
| US-940 | 身為掌舵者，我想只在「研發工作流 → 研究來源設定」設定一次研究來源，自我進化就用同一份，以便不必兩處維護、也不會漂移 | AC-965-1 | Given 遷移到 V24 When 檢視新表與種子 Then 欄位、CHECK、受控守衛、17 列種子與 4 個 FETCH 網域齊備且重跑冪等 |
| US-940 | 同上 | AC-965-2 | Given 遷移到 V25 When 檢視 `si_console_writes.kind` Then CHECK 恰六值、欄寬與觸發器不變 |
| US-940 | 同上 | AC-965-3 | Given Bridge 與 DB When 新增／停用追蹤來源 Then 輸入閘、單一閘、重複 slug、PATCH 規則與大小閘依契約，R2P allowlist 零變動 |
| US-940 | 同上 | AC-965-4 | Given 任一 DB 狀態 When 取登記快照 Then 逐位元組確定、sha 公式成立、黃金檔相符 |
| US-940 | 同上 | AC-965-5 | Given console-api When 三種角色呼叫追蹤來源端點 Then ADMIN 才能寫、審計落 `research_watch_source`、R2P 端點與請求數不變 |
| US-940 | 同上 | AC-965-6 | Given ADMIN 且在名單 When 同步 Then 閘門序、原樣嵌入、冪等、補償與機密不外洩依契約 |
| US-940 | 同上 | AC-965-7 | Given Bridge 當前 digest 與 SI 鏡像 When 查狀態 Then 依序判 synced／pending／unsynced，讀不到為 unknown |
| US-940 | 同上 | AC-965-8 | Given ADMIN 開研究來源設定 When 操作追蹤來源 Then 清單、驗證、自動同步、狀態文案與重試依規格 |
| US-940 | 同上 | AC-965-9 | Given 自我進化頁與對帳面板 When 渲染 Then 一行說明、新 kind 標籤與入帳指令、橫幅三鍵具名呈現與每頁說明同步 |
| US-940 | 同上 | AC-965-10 | Given 真全棧與三寬度 mock When 走完流程與無障礙檢查 Then 稽核檔落地且 axe 零違規、無橫向溢出 |

**本增量交付物**（D1～D9；路徑相對 monorepo 根；三個開發包的持有面見〈提交順序與責任〉）

| 編號 | 交付物 | 路徑 | 製作者 | 主要驗證 |
|------|--------|------|--------|----------|
| D1 | Flyway V24（表、擴充守衛、種子）與 V25（kind 放寬）；版號為 `db/migration/` 現查最大版本＋1 與＋2（撰寫時最大為 V23） | `AgentConsole/backend/src/main/resources/db/migration/V24__research_watch_sources.sql`、`V25__si_console_writes_kind_src_registry.sql` | PKG-BE | AC-965-1、965-2 |
| D2 | backend：追蹤來源端點（API-RP-29；`ResearchController` 加三方法與 `ResearchRegistryService`〔新〕）、`ResearchBridge` 新方法（`watchSources`／`addWatchSource`／`patchWatchSource`／`registry`）、`BridgeHttpAdapter` 實作、`SecurityConfig` 兩條 ADMIN matcher、`ErrorReasons` 的 `REGISTRY_` 三常數、`ResearchErrorDocs` 與 OpenAPI 說明 | `AgentConsole/backend/src/main/java/com/aisdlc/console/`（`adapter/in/web/ResearchController.java` 與 `dto/research/`、`application/service/`、`application/port/out/ResearchBridge.java`、`adapter/out/bridge/BridgeHttpAdapter.java`、`infrastructure/config/SecurityConfig.java`、`domain/exception/ErrorReasons.java`、`adapter/in/web/ResearchErrorDocs.java`） | PKG-BE | AC-965-5 |
| D3 | backend：同步與狀態（API-SI-14／15；`SiController` 加兩方法、`SiWriteUseCase.syncResearchRegistry`、`SiConsoleWriteService` 實作〔取快照走 `ResearchBridge.registry()` 讀取、閘門序 5／6〕、`SiAuditSigner.registrySyncBody`、`SiWriteKind.SRC_REGISTRY`、`AgentBridge.siWriteRegistrySync`、`SiReconcileService` 事件種類對映、狀態 DTO） | 同上 `application/**`、`adapter/in/web/SiController.java`、`domain/model/si/SiWriteKind.java`、`adapter/out/bridge/` | PKG-BE | AC-965-6、965-7 |
| D4 | Bridge：`app/research/registry.py`（新；快照與單一閘純函式）、`routers/research.py`（加四個端點）、`research/db.py`（加 `list_watch_sources`／`add_watch_source`／`set_watch_source_enabled`）、`routers/si.py`（加 `/registry:sync`）；測試與夾具（含 `is_public_ip` 對附錄 A 的 parity 與 `check_watch_url` 對附錄 D 的 parity） | `AgentConsole/engine-bridge/app/`、`tests/test_research_watch_sources.py`、`tests/test_research_registry_snapshot.py`、`tests/test_si_registry_route.py`、`tests/fixtures/research_registry/`（`golden-r1.json`、`seed_si_sources.json`，以及主控自根層附錄抽出的複本 `appendix-a.txt`、`appendix-b.json`、`appendix-d.txt`） | PKG-BR | AC-965-3、965-4、965-6 |
| D5 | frontend 純函式、型別、端點：`lib/domain/researchRegistry.ts`（新）、`lib/api/{endpoints,queries,types}.ts`、`lib/api/schema.d.ts` 重產 | `AgentConsole/frontend/lib/` | PKG-FE | AC-965-8、965-9 |
| D6 | frontend 元件：`WatchSourcesSection.tsx`（新；掛入 `AllowlistDialog`）、網域區共用說明句、`SiView` 說明列、對帳面板新 kind 標籤、`lib/help/research-workspace.ts` 與 `self-improving.ts` | `AgentConsole/frontend/components/domain/research/`、`components/domain/si/`、`lib/help/` | PKG-FE | AC-965-8、965-9 |
| D7 | E2E：`research-docker.stack.spec.ts` 新案、`a11y.mock.spec.ts` 新情境與 mock 路由、`self-improving` 相關 mock spec 補路由 | `AgentConsole/frontend/tests/e2e/` | PKG-FE | AC-965-10 |
| D8 | 既有釘選測試同步（只改預期值；逐項見 §4.1） | §4.1 | 三包各自持有面 | NFR-RR-5 |
| D9 | 出口實查（V 系列，非 AT） | §6.2 的 V1～V8 | QA、主控、掌舵者 | PRD FR-R2P-24 |

**提交順序與責任**

- 依賴序：**根層實作輪先產出 G-S1（`tools/tests/fixtures/selfimproving/G-S1.audit.json`，依根層附錄 C 的固定輸入）→ 主控原樣複製到 `AgentConsole/backend/src/test/resources/si/G-S1.audit.json` 與 Bridge 測試夾具 → PKG-BE（V24／V25；Java 以附錄 C 的同一組輸入〔金鑰、`audit_ref`、帳號、`time`、附錄 B 的 `registry_text`〕重新產生 body 與外層檔並斷言與副本位元組相等）→ PKG-BR 消費附錄 A／B／D 複本與 G-R1（G-R1 由 PKG-BR 以 `json.dumps` 現算並核對契約 §5A.3 的 sha）→ PKG-FE 可與 PKG-BE 並行開工純函式與元件，但 `schema.d.ts` 須待 PKG-BE 完成後以拋棄式 IT 倒 `/v3/api-docs` 餵 `scripts/gen-api.mjs` 重產入庫**（沿 P2b 勘誤 9 作法）。每支程式完成即編譯並跑該區 AT，不累積（`AgentConsole/CLAUDE.md` 鐵律 11）。
- **三包持有面互不重疊、可並行**（根鐵律七）：PKG-BE＝`AgentConsole/backend/**`（含 Flyway 新檔）；PKG-BR＝`AgentConsole/engine-bridge/**`；PKG-FE＝`AgentConsole/frontend/**`。共用物只有共享附錄與黃金檔：附錄 A／B／D 的複本（**主控**自根層 TCS 圍欄內文字抽出，複製到 Bridge 與前端各自的夾具目錄；backend 的「原樣嵌入」AT 使用附錄 B 的複本 `src/test/resources/research-registry/appendix-b.json`）、G-R1（PKG-BR 產出）與 G-S1（根層產出、主控複製到 backend 與 Bridge）；各複本與根層本文的位元組 sha256 由各側測試先驗；三包之間不得互相修改對方的目錄。
- 開發 agent **不 commit／push**、不動根層 `tools/`、`.github/`、`.claude/`、凍結檔與既有 TCS（鐵律 7）。`Architecture.md` 不改（§7.1 第 10 項）；契約 §5A 升 v1.0、RTM 本地子表、SCG-4 報告、`lib/help/*` 的頁面說明（與 UI 實作同 commit）由主控代做。
- 真 SI 家目錄 `~/.autosdd/`、真帳本、真事件帳本一律唯讀且**不得被任何 AT 寫入**：AT 只用 Testcontainers PG、迷你 Bridge、jsdom、fetch 替身與 Playwright 路由替身；Docker 全棧 E2E 的 `BRIDGE_SI_AUDIT_DIR` 必須指向全棧自帶的容器卷（不得掛真 SI 家目錄；AT-965-10-1 斷言之）。

**〈增量行為規則〉**（W-R0～W-R10；各 AT 以 W-R 編號引用。實查依據：契約 §5A、PRD FR-R2P-24；現行測試 `ResearchSchemaMigrationIT`、`SiConsoleWritesMigrationIT`、`BackupJobMigrationIT`、`ResearchApiIT`、`RbacIT`、`OpenApiIT`、`ResearchReasonsTest`、`ResearchArchTest`、`SiConsoleWriteApiIT`、`SiConsoleWritesReadApiIT`、`SiAuditSignerTest`、`SiReadOnlyArchTest`、`AbstractSiWriteIT`；Bridge `tests/test_research_router.py`、`test_si_write_routes.py`、`test_si_audit_filename_safety.py`、`test_si_console_ingest.py`、`test_si_readonly_lock.py`；frontend `AllowlistDialog.test.tsx`、`SiView.test.tsx`、`lib/domain/si.test.ts`、`lib/help/content.test.ts`、`pageFacts.test.ts`）

- **W-R0 R2P 零退步**：本鍵不改 API-RP-22 三個端點、`check_research_url`、研究 run 的有效清單與 `allowlist_snapshot` 形狀、既有 reason 集合（`RESEARCH_` 前綴三十七個）；既有 AT 的預期值只因「遷移版本與表數」「OpenAPI 計數」「種子帶來的列」三類原因改動（§4.1 逐項）。
- **W-R1 V24**：表 `console.research_watch_sources`（欄位與 CHECK 逐字見契約 §5A.1）；主鍵 `slug`；`url` 的 CHECK 正規式為 `^https://[a-z0-9]([a-z0-9.-]*[a-z0-9])?([/?][^[:space:]#]*)?$` 加 `char_length(url) <= 500`（以 `VARCHAR(500)`）；`expand_*` 三欄同空同非空；停用欄 CHECK；觸發器掛既有通用守衛，守衛函式以 `CREATE OR REPLACE` 增第十條允許清單（`enabled`／`disabled_by`／`disabled_at`），九條既有條目與函式其餘文字逐字不動；種子 17 列與 4 個 FETCH 網域（`ON CONFLICT DO NOTHING`）；**不種 WEB**、不種 `raw.githubusercontent.com` 與 `platform.openai.com`；種子時間取固定常數 `2026-11-10T00:00:00+00:00`。
- **W-R2 V25**：`si_console_writes_kind_check` 先現查存在才 `DROP` 再 `ADD`，六值；欄寬與觸發器不動。
- **W-R3 Bridge 追蹤來源**：輸入閘規則名與 **URL 原樣判定（不正規化；D-EQA-1 原則：Console 接受集合 ⊆ SI 接受集合，逐列等於附錄 D 的 CON 欄）**、單一閘、大小閘、PATCH 規則、重新啟用清空停用欄、不寫 `research_events`、`bridge.audit` 每次寫入多一筆（契約 §5A.2）。DB `url` CHECK 亦逐列等於附錄 D 的 CON 欄（契約 §5A.1：除基本形狀外另拒 `xn--` label、`localhost`／`*.localhost`、IPv4 字面）。
- **W-R4 登記快照**：契約 §5A.3 正規化規則六點逐字；黃金檔 G-R1 與附錄 B golden；確定性（同狀態同位元組、與插入順序無關）；`is_public_ip` 與附錄 A 逐列相符（Bridge 與根層兩份實作的 parity）。
- **W-R5 console-api 追蹤來源**：角色（GET 三角色、POST／PATCH ADMIN）、輸入閘先於 Bridge、V6 `audit_log` 落 `entity_type='research_watch_source'` 與 `entity_id=<slug>`、`AuditTrail.note`、Bridge 錯誤逐字透傳。
- **W-R6 同步端點**：契約 §5A.4 閘門序七關；冪等只比最新一筆；補償與結果不明語意同 P2b；稽核 body 的兩欄原樣嵌入；外層檔≤65536。
- **W-R7 狀態與對帳**：契約 §5A.4 的判定序五步；`research.registry` 事件對映 `src-registry`；`researchFetchMax` 只轉鏡像值。
- **W-R8 前端區塊**：清單、新增驗證、停用／重新啟用、自動同步（每次成功的新增／停用／重新啟用後恰一次）、失敗文案、狀態三態＋量不到、手動鈕、網域區共用說明句；不持有 deciders 名單。
- **W-R9 自我進化頁與說明**：一行說明（ADMIN 帶連結）、對帳面板新 kind 標籤與 `ingestCommands`、每頁說明與既有鎖。
- **W-R10 E2E 與無障礙**：真棧流程與 mock 情境；三寬度 1440／1000／600（沿 `a11y.mock.spec.ts` 的 `RESEARCH_WIDTHS`）axe 零違規且無橫向溢出。

**非功能需求（NFR-RR）**

| NFR | 敘述 | 驗證 AT |
|-----|------|---------|
| NFR-RR-1 | **零副作用的拒絕**：同步端點序 1～6 任一拒絕前後，`si_console_writes` 列數、迷你 Bridge 的寫入請求數、ref 來源取用次數的變動量皆為 0（序 4、5 的讀取請求須逐項斷言）；追蹤來源 POST／PATCH 被拒時 `research_watch_sources` 零變動 | AT-965-6-2、AT-965-5-1、AT-965-3-2 |
| NFR-RR-2 | **快照確定性**：同一 DB 狀態與部署基底→逐位元組相同的 `registry_text`；digest 對「同內容」恆同（含停用後重新啟用）；快照路徑不讀時鐘 | AT-965-4-1、4-2、4-6、4-9 |
| NFR-RR-3 | **寫入不生效即不宣稱生效**：同步 201 與狀態 `pending` 的文案一律為「稽核檔已落地，待入帳」類，不得出現「已同步」「已生效」；只有 `synced`（SI 鏡像 `research_registry.registry_sha256`＝當前 digest）才顯示「已同步」 | AT-965-6-1、AT-965-8-5 |
| NFR-RR-4 | **量不到不顯示成已同步或零**：鏡像或帳本讀不到＝`unknown` 加原因；`researchFetchMax` 缺席＝不顯示數字警示 | AT-965-7-2、AT-965-7-4、AT-965-8-2 |
| NFR-RR-5 | **零退步與範圍**：既有 AT 在其角色下仍綠，釘選數字只改預期值（§4.1）；只動 §5.7 允許集合；既有 reason 鎖零改動 | AT-965-3-E-1、AT-965-5-5、V4 |
| NFR-RR-6 | **機密不外洩**：簽章金鑰與寫入權杖值不出現在回應、日誌、畫面與測試輸出；狀態端點不回稽核 body、`mac` 與金鑰 | AT-965-6-8、AT-965-7-3 |
| NFR-RR-7 | **跨平台**（根鐵律三）：新程式與測試不引入平台專屬假設；Windows 與 Linux（CI）皆須全綠；macOS 未驗 | V6 |
| NFR-RR-8 | **開發 agent 交卷前閘門**（輸出逐字貼入）：(1) 本檔各 AT 逐一單跑；(2) `gradlew clean build`；(3) 前端 lint、`tsc --noEmit`、build、vitest；(4) Bridge `pytest`、`ruff check`（本目錄與 monorepo 根視角各一次）；(5) 讀 rc 先存變數再讀；(6) 不 commit、不碰根層 `tools/`、`.claude/`、凍結檔；(7) 夾具與測試中不得出現不存在於真帳本的字面 `PROP-SI-`、`OBS-SI-`、`RUN-SI-` 接數字；(8) 不得有 `sk-` 形態字串與真機密；(9) 契約與實作不符處以純文字回報；(10) 交卷含流程摩擦節 | SCG-4 實跑檢核 |
| NFR-RR-9 | **hermetic**：AT 不得寫真 SI 家目錄；E2E 的稽核目錄為全棧容器卷；測試產生的追蹤來源列 `slug` 一律以 `e2e-` 或 `t-` 前綴，E2E 收尾以 PATCH 停用（列只增不刪，這是設計） | AT-965-10-1 |

**追溯矩陣**：F-940 ← PRD FR-R2P-24（AC-R2P-24-1～24-10）、§2.1.1 權限矩陣、§7.3 頁面 0、§9.2、§12.1 第 16 列、附錄 C.8 D-169～D-176；契約 §5A；根層 SelfImproving PRD v0.15 的對映 FR 與根層 TCS 的接縫條文；P2b 的稽核管線（W10、W11、W14、W15）與 P4 的同型放寬（W-S7）；US-R2P-24 → AC-965-1～10（本檔 FRD-lite）→ AT（本檔 §1）。

**〈增量追溯表〉**（SCG-0～3；「已凍結上位文件」相對 `spec-frozen --root`＝monorepo 根；**凍結摘要一律由主控於凍結前以 `Get-FileHash -Algorithm SHA256` 重算並與各鍵 `show --json` 的 `frozen_stages[-1].spec_doc_digests` 對照，不符以 `show` 為準**；下表摘要為 SD 棒 2026-11-10 對 HEAD 工作樹檔案現算，`ResearchToPRD_PRD.md` 與 `API_Contract_ResearchToPRD.md` 兩列為**本增量修訂前**的凍結值，修訂後必然改變，隨三把 R2P 鍵 refreeze 更新）

| 清單項（閘門／項目） | 追溯 ID | 已凍結上位文件（路徑） | 凍結摘要 |
|---------------------|---------|----------------------|---------|
| SCG-0／PRD 版本已鎖定、FRD 覆蓋、利害關係人已簽核 | FR-R2P-24、US-R2P-24、AC-R2P-24-1～24-10；授權＝sid `58ce5ccd-13fb-47fc-8a46-b04fa73257d7` line 14；凍結常態規則（根 CLAUDE.md） | docs/01_requirements/ResearchToPRD_PRD.md | sha256:d947094c11a5f8ec46424ca277abc2d0f34a17f82ccd856527b2751b4017baab（增量修訂前；與 `agentconsole-research-to-prd-p2` 最後凍結值相同） |
| SCG-0／根層 PRD（SI 側契約的唯一定稿處） | SelfImproving PRD v0.15 對映 FR（根層棒；本檔引用不複寫） | docs/01_requirements/SelfImproving_PRD.md | sha256:25bec84cd2fd99c95980a87050ada72201dfc7cfd50f390e6bf58b16b047795c（v0.14 現值；根層棒改 v0.15 後主控重算） |
| SCG-0／NFR 已量化、User Story INVEST、RTM 初版 | NFR-RR-1～9；US-R2P-24；本檔 §1 與 §6（RTM 本地子表於 SCG-5 回填） | （本檔；隨 Stage 凍結，非上位文件） | n/a（自引） |
| SCG-1／整合架構、NFR 對應 | Architecture §5（前端）、§7（資料所有權）、§10（Bridge 契約）、§11（契約簡表；本鍵不改，§7.1 第 10 項） | AgentConsole/docs/02_architecture/Architecture.md | sha256:388abdd7499d85375ca08e5c295e2b018c6a3942dab2210b15565c1b234cb471 |
| SCG-1／技術選型與偏離清單 | ADR-001（Spring Boot 4.1、JDBC adapter 體例、PG18、Flyway）；ADR-003（研究抓取 allowlist 決策 D7、全域資源不寫事件帳） | AgentConsole/docs/02_architecture/ADR-001-TechStack-Lock.md；AgentConsole/docs/02_architecture/ADR-003-ResearchToPRD.md | sha256:ff0bcd0038b77e80885240d287cfc68fb55c02200dc59f62f7e59c7691094e38；sha256:8507064f6b78abffac57e2a7d5ca516853744499a97308555d927749c61e1e0f |
| SCG-3／API Spec、錯誤碼、Consumer Contract | 契約 API-RP-22（不變）與 §0.2、§2.1、§2.2；本鍵新增 §5A（API-RP-29、API-SI-14／15、Bridge 五端點、快照規則、G-R1，並引用根層附錄 B golden） | AgentConsole/docs/02_architecture/API_Contract_ResearchToPRD.md | sha256:e003ee2c8e1ce035dad367f1892c64fc2424e47cd5dc546ee18180cf5aa2a85d（增量修訂前） |
| SCG-3／前代契約（P2b 稽核管線與補償語意；P4 同型放寬） | `API_Contract_SelfImproving_P2b.md` §0.1～§0.4、§1.2、§1.4、§2.1、§3.2～§3.4、§4；`API_Contract_SelfImproving_P2c.md`（同型 kind 放寬、序 5′ 先例） | AgentConsole/docs/02_architecture/API_Contract_SelfImproving_P2b.md；AgentConsole/docs/02_architecture/API_Contract_SelfImproving_P2c.md | sha256:32e60de75fda6171a452d28449567aa19e5ade8825e3fcc27e35edd795b92841；sha256:7e3b3d7ccdf0a5ff7910a85f6615b8a594c5718d02aa225d029e426d116dda67 |
| SCG-3／上位 TCS | `TCS-ResearchToPRD-P0／P1／P2`（AT-960-1-1、1-4、5-4、5-5、8-9、19-8；AT-961-1-1、1-E-1；AT-962-1-1、1-6）；`TCS-SelfImprovingSchedule-20261109.md`（W-S7、AT-964-7-6、7-7）；`TCS-SelfImprovingDecideDedupe-20261031.md`（對帳面板與取代群組；本鍵不改其行為） | AgentConsole/docs/03_testing/contracts/TCS-ResearchToPRD-P0-20261102.md；…-P1-20261107.md；…-P2-20261107.md；TCS-SelfImprovingSchedule-20261109.md；TCS-SelfImprovingDecideDedupe-20261031.md | sha256:8ba3703b013de076492fe621885100e71cad603c0bab25dd11fe33c17e3c3e8d；sha256:14c600d2b9a1e46e70cfeae487bf85638ddd79fc159f41fc0f7b7ef5747c75cc；sha256:7a34a06fc8f1abad86ce1c74ee8dfcdd0217cf0a6302369584db9429f649f4d2；sha256:2fc762ad7b13923d0d5e1bc5c19510ae32c73c127ebcf8050555b83517d02544；sha256:29a4db6bf25721a78413d8bd1072e33399d4b7b8f933a595791866db86f65b0e |
| SCG-3／根層 TCS（接縫） | 根層 TCS 的 `research.registry` 事件（D-RR-14）、`src-registry` body 與位元組表（D-RR-17）、CLI 入帳動詞、SI `status` 的 `research_fetch_max` 與 `research_registry`（D-RR-15）（本檔引用不複寫） | docs/03_testing/contracts/TCS-SelfImproving-P6-20261110.md | （根層棒產出中；主控於凍結前填入） |

---

## 1. AC → AT 映射表

> 每個 AC 對應至少一個可自動化 AT；AT ID 前兩段數字＝所屬 AC。

| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
|-------|---------|-------|---------|-------|---------|------|
| AC-965-1 | V24 表、守衛、種子 | AT-965-1-1 | 欄位、CHECK 與主鍵逐項 | ✅ | Integration | □ |
| AC-965-1 | | AT-965-1-2 | 受控更新守衛矩陣與重新啟用清空停用欄 | ✅ | Integration | □ |
| AC-965-1 | | AT-965-1-3 | 追蹤來源種子 17 列與 SI 舊表逐字對拍 | ✅ | Integration | □ |
| AC-965-1 | | AT-965-1-4 | 網域種子四列、WEB 零新增、不種停用列網域 | ✅ | Integration | □ |
| AC-965-1 | | AT-965-1-5 | 種子重跑冪等 | ✅ | Integration | □ |
| AC-965-1 | | AT-965-1-6 | 通用守衛函式重定義不退步（九條既有允許清單逐條對拍） | ✅ | Integration | □ |
| AC-965-1 | | AT-965-1-7 | `url` CHECK 負控與正控 | ✅ | Integration | □ |
| AC-965-1 | | AT-965-1-E-1 | 既有表升級零變動（BackupJob 前後快照）與 research_ 表守衛不退步 | ✅ | Integration | □ |
| AC-965-2 | V25 kind 放寬 | AT-965-2-1 | CHECK 六值、約束名與欄寬不變 | ✅ | Integration | □ |
| AC-965-2 | | AT-965-2-2 | 新 kind 可寫入且列不可改的觸發器不變 | ✅ | Integration | □ |
| AC-965-2 | | AT-965-2-3 | 自 V23 升級：既有列逐列不變 | ✅ | Integration | □ |
| AC-965-3 | Bridge 追蹤來源 CRUD 與單一閘 | AT-965-3-1 | POST 正控與副作用面 | ✅ | Integration | □ |
| AC-965-3 | | AT-965-3-2 | 六條輸入閘規則一次全列 | ✅ | Integration | □ |
| AC-965-3 | | AT-965-3-3 | URL 原樣判定＝附錄 D CON 欄逐列 | ✅ | Unit | □ |
| AC-965-3 | | AT-965-3-4 | 單一閘 `host_not_allowed` | ✅ | Integration | □ |
| AC-965-3 | | AT-965-3-5 | 重複 slug 與 slug 永不重用 | ✅ | Integration | □ |
| AC-965-3 | | AT-965-3-6 | PATCH 規則與重新啟用 | ✅ | Integration | □ |
| AC-965-3 | | AT-965-3-7 | 停用網域後的追蹤來源狀態 | ✅ | Integration | □ |
| AC-965-3 | | AT-965-3-8 | 大小閘邊界 | ✅ | Integration | □ |
| AC-965-3 | | AT-965-3-9 | 讀端、排序、無 DSN 與權杖 | ✅ | Integration | □ |
| AC-965-3 | | AT-965-3-E-1 | R2P allowlist 端點零變動 | ✅ | Integration | □ |
| AC-965-4 | 登記快照 | AT-965-4-1 | 黃金檔 G-R1 位元組與 sha | ✅ | Integration | □ |
| AC-965-4 | | AT-965-4-2 | 確定性與插入順序無關 | ✅ | Integration | □ |
| AC-965-4 | | AT-965-4-3 | `hosts` 規則與位元組序 | ✅ | Unit | □ |
| AC-965-4 | | AT-965-4-4 | `min_interval_seconds` 算式 | ✅ | Unit | □ |
| AC-965-4 | | AT-965-4-5 | `watch` 全列、時間與 `expand` 形狀 | ✅ | Integration | □ |
| AC-965-4 | | AT-965-4-6 | 停用／重新啟用網域與 digest 往返 | ✅ | Integration | □ |
| AC-965-4 | | AT-965-4-7 | sha 公式與位元組衛生 | ✅ | Unit | □ |
| AC-965-4 | | AT-965-4-8 | 超界與無 DSN | ✅ | Integration | □ |
| AC-965-4 | | AT-965-4-9 | 快照路徑不讀時鐘（靜態） | ✅ | Unit | □ |
| AC-965-4 | | AT-965-4-E-1 | `is_public_ip` 對附錄 A 逐列 | ✅ | Unit | □ |
| AC-965-4 | | AT-965-4-E-2 | 以附錄 B 列內容為 DB 夾具，`GET /research/registry` 逐位元組等於附錄 B | ✅ | Integration | □ |
| AC-965-5 | console-api 追蹤來源端點 | AT-965-5-1 | 角色矩陣與零 Bridge 請求 | ✅ | Integration | □ |
| AC-965-5 | | AT-965-5-2 | ADMIN 寫入的審計與事件帳不變 | ✅ | Integration | □ |
| AC-965-5 | | AT-965-5-3 | 輸入閘 400 先於 Bridge | ✅ | Integration | □ |
| AC-965-5 | | AT-965-5-4 | Bridge 錯誤逐字透傳 | ✅ | Integration | □ |
| AC-965-5 | | AT-965-5-5 | R2P allowlist 端點回應與請求數不變 | ✅ | Integration | □ |
| AC-965-5 | | AT-965-5-6 | OpenAPI 操作與 DTO | ✅ | Integration | □ |
| AC-965-5 | | AT-965-5-E-1 | ArchUnit：呼叫面與零寫入掃描 | ✅ | Unit | □ |
| AC-965-6 | 同步端點 | AT-965-6-1 | 正控：簽章、原樣嵌入、落檔位元組 | ✅ | Integration | □ |
| AC-965-6 | | AT-965-6-2 | 閘門序表驅動與零副作用 | ✅ | Integration | □ |
| AC-965-6 | | AT-965-6-3 | 冪等判定表 | ✅ | Integration | □ |
| AC-965-6 | | AT-965-6-4 | 補償與結果不明 | ✅ | Integration | □ |
| AC-965-6 | | AT-965-6-5 | 外層檔超界 | ✅ | Integration | □ |
| AC-965-6 | | AT-965-6-6 | Bridge `/si/registry:sync` 落檔 | ✅ | Integration | □ |
| AC-965-6 | | AT-965-6-7 | G-S1：Console 副本＝根層檔，Java 重新產生位元組相等 | ✅ | Integration | □ |
| AC-965-6 | | AT-965-6-9 | 冪等：D→E（待入帳）→D 照常送出 | ✅ | Integration | □ |
| AC-965-6 | | AT-965-6-8 | 機密不外洩 | ✅ | Integration | □ |
| AC-965-6 | | AT-965-6-E-1 | ArchUnit：唯一呼叫面與唯讀鎖不退步 | ✅ | Unit | □ |
| AC-965-7 | 同步狀態與對帳 | AT-965-7-1 | 四態判定表 | ✅ | Integration | □ |
| AC-965-7 | | AT-965-7-2 | `unknown` 原因與主資料失敗 | ✅ | Integration | □ |
| AC-965-7 | | AT-965-7-3 | 回應鍵集合與角色 | ✅ | Integration | □ |
| AC-965-7 | | AT-965-7-4 | `researchFetchMax` 只轉鏡像值 | ✅ | Integration | □ |
| AC-965-7 | | AT-965-7-5 | 對帳讀面新 kind | ✅ | Integration | □ |
| AC-965-8 | 前端追蹤來源區與同步 | AT-965-8-1 | 純函式：表單驗證與請求本文 | ✅ | Unit | □ |
| AC-965-8 | | AT-965-8-2 | 清單渲染與警示 | ✅ | Integration | □ |
| AC-965-8 | | AT-965-8-3 | 新增流程與自動同步 | ✅ | Integration | □ |
| AC-965-8 | | AT-965-8-4 | 停用與重新啟用 | ✅ | Integration | □ |
| AC-965-8 | | AT-965-8-5 | 同步狀態列文案 | ✅ | Integration | □ |
| AC-965-8 | | AT-965-8-6 | 同步錯誤文案與重試 | ✅ | Integration | □ |
| AC-965-8 | | AT-965-8-7 | 手動同步鈕與併發去重 | ✅ | Integration | □ |
| AC-965-8 | | AT-965-8-8 | 角色與既有 AT-960-19-8 不退步 | ✅ | Integration | □ |
| AC-965-8 | | AT-965-8-E-1 | 靜態掃描 | ✅ | Unit | □ |
| AC-965-8 | | AT-965-8-E-2 | 鍵盤、焦點與 aria | ✅ | Integration | □ |
| AC-965-9 | 自我進化頁、對帳標籤、說明 | AT-965-9-1 | `SiView` 一行說明 | ✅ | Integration | □ |
| AC-965-9 | | AT-965-9-2 | 對帳面板新 kind | ✅ | Integration | □ |
| AC-965-9 | | AT-965-9-3 | 每頁說明與既有說明鎖 | ✅ | Unit | □ |
| AC-965-9 | | AT-965-9-4 | `schema.d.ts` 與端點函式 | ✅ | Unit | □ |
| AC-965-9 | | AT-965-9-5 | 橫幅三鍵具名呈現（研究來源、同步、反事實回測） | ✅ | Integration | □ |
| AC-965-10 | E2E 與無障礙 | AT-965-10-1 | Docker 全棧：種子、新增、同步、稽核檔 | ✅ | E2E | □ |
| AC-965-10 | | AT-965-10-3 | Bridge 映像預建稽核目錄（具名卷擁有者；E-11） | ✅ | Unit | □ |
| AC-965-10 | | AT-965-10-2 | 三寬度 axe 與溢出 | ✅ | E2E | □ |
| AC-965-10 | | AT-965-10-4 | ADMIN 自我進化頁的研究來源說明連結無對比違規（mock axe；E-14） | ✅ | E2E | □ |
| AC-965-10 | | AT-965-10-E-1 | 非名單 ADMIN 的同步被拒（mock） | ✅ | E2E | □ |

**覆蓋率統計**：總 AC 數 10；已映射 AT 數 74；映射覆蓋率 100%。

---

## 2. 可自動化 AT 格式規範

> **驗收字樣與判定指令**：每個 AT 的「判定」行給判定指令；每個 AT 的最後一行「驗收字樣」帶一個以方括號包住的字樣（形態：`AT_OK_` 接 AT 底線形去掉 `AT_` 前綴的部分；E 類的 `E` 保留）。本 Feature 走 SDD session-only 路徑：實作者在 session 內自跑判定指令，**把輸出逐字貼進證據**（沒貼＝未驗證），並在最終回覆逐 AT 列出驗收字樣。
>
> **AT 底線形**＝把 AT ID 的連字號換成底線（`AT-965-6-3` 的底線形是 `AT_965_6_3`）；每個 AT 的測試函式（Java 為方法、pytest 為函式、vitest 為 `it` 名稱、Playwright 為 `test` 名稱）須含其底線形。**同一 AT 的子情境**一律以參數化或 `subTest`／`it.each`／`@ParameterizedTest` 實作並保留底線形，任一子情境失敗時失敗訊息須指出是哪一個。**不得新增 skip 或 `it.skip`／`describe.skip`／`test.skip`／`@Disabled`**：Docker 缺席視為環境壞、直接失敗。AT 內不引用其他 AT 的 ID。
>
> **判定指令的四種形態**（PowerShell 不用裸 `cd`，用 `Push-Location … Pop-Location` 同行成對，讀 rc 先存變數再讀）：backend `gradlew test --tests "<類別全名>.<AT 底線形>*"`（cwd＝`AgentConsole/backend`；整合測試需 Docker）；Bridge `python -m pytest <檔> -k <AT 底線形> -q`（cwd＝`AgentConsole/engine-bridge`，根層 `.venv`）；frontend `npx vitest run <檔> -t <AT 底線形>`（cwd＝`AgentConsole/frontend`）；Playwright `npx playwright test <檔> -g <AT 底線形>`（cwd＝`AgentConsole/frontend`；mock 情境 `E2E_MODE=standalone`，真棧 `E2E_STACK=1` 並帶 `E2E_ADMIN_*`）。
>
> **斷言簡寫**（資料與設施細節見 §5）：**backend**：`ADMIN`（帳號 admin，在 `console.si.deciders`、金鑰與權杖已設）、`ADMIN2`（ADMIN 角色但不在 `console.si.deciders`）、`OPERATOR`、`VIEWER`、`MINI`（迷你 Bridge；本鍵加 `MINI.registry(text, sha)` 設定 `GET /research/registry` 的回應、`MINI.watch.*` 記錄追蹤來源端點收到的請求、`MINI.si.writes` 記錄 `/si/registry:sync` 收到的位元組、`MINI.status(...)`／`MINI.events(...)` 設定 SI 鏡像讀取）、`SEAM`（`SiWriteSeam` 排入 ref）、`rows()`（`si_console_writes` 逐列內容含 body 位元組）、`refs`（`SiAuditRefSource` 取用次數）、`K0`（固定金鑰）；**Bridge**：`LB`（本機 Bridge 測試夾具）、`RDB`（真 PG 夾具；追蹤來源與快照測試須用真 PG，因 CHECK 與守衛在 DB）、`ENV(hosts)`（部署基底設定）；**frontend**：`renderResearchDialog`（沿 `AllowlistDialog.test.tsx` 的渲染輔助）、fetch 替身與 `overrides` 沿 P2b、`ADMIN_UI`／`OPERATOR_UI`／`VIEWER_UI`、`WS(over)`（一列 `WatchSourceDto` 夾具，逐鍵覆寫）、`STATUS(state, over)`（`ResearchRegistrySyncStatus` 夾具）。

**A. 資料庫（backend；類別 `ResearchWatchSourceSchemaIT` 新增，`AbstractPgIT` 體例）**

- **AT-965-1-1**（JUnit｜`ResearchWatchSourceSchemaIT`｜Integration｜AC-965-1、W-R1；AC-R2P-24-1）`console.research_watch_sources` 的欄位、型別、可空、預設與全部 CHECK 逐項成立。
  - Given Testcontainers PG 遷移至最新版
  - When 查 `information_schema.columns`、`pg_constraint`（`pg_get_constraintdef`）與主鍵
  - Then 欄位依序為 `slug`、`url`、`kind`、`extract`、`layer`、`expand_mode`、`expand_prefix`、`expand_max`、`enabled`、`added_by`、`added_at`、`disabled_by`、`disabled_at`，型別與長度同契約 §5A.1；主鍵恰 `slug`；`kind` 六值、`layer` 四值、`expand_mode` 兩值、`expand_max` 1～3 各由 CHECK 擋列舉外值（逐值探針：每個合法值可 INSERT、緊鄰的非法值被擋）；`expand_*` 三欄「全空或全非空」（兩空一非空、一空兩非空共六種混合形態皆被擋）；`enabled=false` 而 `disabled_by` 或 `disabled_at` 為空被擋；`extract` 為空字串或含控制字元（`\u0000`、`\n`、`\u007f`）被擋、200 字元通過、201 字元被擋；`added_at` 預設為現在且帶時區
  - 判定：`gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchWatchSourceSchemaIT.AT_965_1_1*"`；預期突變：拿掉任一 CHECK、把主鍵改非 slug、把 `added_at` 改無時區、放寬 `expand_max` 上界，皆至少一個子情境紅
  - 驗收字樣：[AT_OK_965_1_1]
- **AT-965-1-2**（JUnit｜`ResearchWatchSourceSchemaIT`｜Integration｜AC-965-1、W-R1；AC-R2P-24-1）受控更新守衛：只放行三欄、同句夾帶非允許欄整句被擋、DELETE 被擋、重新啟用可清空停用欄。
  - Given 一列啟用中的追蹤來源與一列停用中的
  - When 逐欄 UPDATE 每個非允許欄（`url`、`kind`、`extract`、`layer`、三個 `expand_*`、`added_by`、`added_at`、`slug`）；同句 `SET enabled=false, url='…'`；`DELETE`；`UPDATE SET enabled=false, disabled_by='a', disabled_at=now()`；對停用列 `UPDATE SET enabled=true, disabled_by=NULL, disabled_at=NULL`
  - Then 非允許欄 UPDATE 與同句夾帶皆被拒、SQLSTATE 類別 23、訊息含表名、列不變（逐列快照相等）；`DELETE` 被拒；合法停用成功；重新啟用成功且 `disabled_by`、`disabled_at` 為 NULL；`enabled=true` 而 `disabled_by` 非空（重新啟用不清空）亦不被 CHECK 擋（Bridge 規則才負責清空，由 AT-965-3-6 守）
  - 判定：`gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchWatchSourceSchemaIT.AT_965_1_2*"`；預期突變：守衛允許清單多放一欄（例 `url`）、少放 `disabled_at`、拿掉 `DELETE` 擋，皆紅
  - 驗收字樣：[AT_OK_965_1_2]
- **AT-965-1-3**（JUnit｜`ResearchWatchSourceSchemaIT`｜Integration｜AC-965-1、W-R1；AC-R2P-24-1）種子恰 17 列，15 列與 SI 舊表逐字相等，啟用 10、停用 7。
  - Given 遷移至最新版的空庫；夾具 `seed_si_sources.json`（byte-identical 複本，取自 `docs/06_quality/SelfImproving_Protocol/research_sources.json` 於 commit `8b6950d2`，檔案 sha256 為 `6201d066799e7f13c18053f3474f6883fddd8091baf0ab24e3a4b1c0d348e26f`；AT 先驗夾具 sha 相符，防夾具漂移）
  - When 讀全表
  - Then 列數 17；夾具 15 個 `id` 皆在表內且 `url`、`kind`、`extract` 逐字相等（`retired:true` 者 `enabled=false`、其餘 `enabled=true`，其中 `anthropic-engineering` 另被停用）；`anthropic-research`（`kind=sitemap`、`expand=(sitemap,/research/,3)`、啟用）與 `arxiv-agents`（`kind=search`、`layer=ACADEMIC`、無 `expand`、啟用；`url` 逐字等於 `https://export.arxiv.org/api/query?search_query=%28abs:%22self-improving%22+OR+abs:%22self-evolving%22+OR+abs:%22agent+memory%22%29+AND+%28cat:cs.AI+OR+cat:cs.CL+OR+cat:cs.SE%29&sortBy=submittedDate&sortOrder=descending&max_results=10`，D-RR-16）存在；啟用恰 10、停用恰 7（6 個 retired 加 `anthropic-engineering`）；`anthropic-engineering` 的 `disabled_by` 為 `migration:V24（以 anthropic-research 取代）`；其餘 SI 匯入列 `added_by` 為 `migration:V24（SI research_sources.json 匯入）`、新兩列為 `migration:V24（研究來源單一化種子）`；所有 `added_at`、停用列的 `disabled_at` 皆為 `2026-11-10T00:00:00+00:00`
  - 判定：`gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchWatchSourceSchemaIT.AT_965_1_3*"`；預期突變：漏種一個 id、改一個 `extract` 字元、把 retired 種成啟用、啟用數變 11，皆紅
  - 驗收字樣：[AT_OK_965_1_3]
- **AT-965-1-4**（JUnit｜`ResearchWatchSourceSchemaIT`｜Integration｜AC-965-1、W-R1；AC-R2P-24-1）網域種子恰四列 FETCH、WEB 零新增、不種停用列的網域。
  - Given 遷移前後的 `research_allowlist_entries` 快照（升級自 V23 的庫，以及空庫）
  - When 比對
  - Then 多出恰四列：`www.anthropic.com`（INDUSTRY）、`github.com`（OSS）、`code.claude.com`（INDUSTRY）、`developers.openai.com`（INDUSTRY），皆 `list_kind='FETCH'`、`min_interval_seconds=5`、`enabled=true`、`tos_acknowledged=false`、`added_by='migration:V24（自我進化研究來源種子）'`；`list_kind='WEB'` 列數前後相同；不含 `raw.githubusercontent.com`、`platform.openai.com`、`export.arxiv.org`；每個**啟用**的種子追蹤來源其 host 皆在上述四個網域或部署基底四組（以固定基底清單常數比對）
  - 判定：`gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchWatchSourceSchemaIT.AT_965_1_4*"`；預期突變：把某網域種進 WEB、多種一個網域、漏種一個，皆紅
  - 驗收字樣：[AT_OK_965_1_4]
- **AT-965-1-5**（JUnit｜`ResearchWatchSourceSchemaIT`｜Integration｜AC-965-1、W-R1；AC-R2P-24-1）種子的 INSERT 語句重跑冪等。
  - Given 已遷移的庫；自遷移檔擷取的種子 INSERT 段（測試以字串擷取 `INSERT INTO console.research_` 起的語句，擷取範圍非空並有負控）
  - When 再執行一次；並在執行前手動停用一個種子列
  - Then 兩張表列數不變、被手動停用的列保持停用（`ON CONFLICT DO NOTHING` 不覆寫）、沒有任何錯誤；Flyway `migrate` 再跑一次 `migrationsExecuted` 為 0
  - 判定：`gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchWatchSourceSchemaIT.AT_965_1_5*"`；預期突變：種子改用 `ON CONFLICT DO UPDATE` 或無衝突子句，皆紅
  - 驗收字樣：[AT_OK_965_1_5]
- **AT-965-1-6**（JUnit｜`ResearchWatchSourceSchemaIT`｜Integration｜AC-965-1、W-R1、D-176(2)；AC-R2P-24-1）通用守衛函式重定義後，九條既有允許清單一字未變、第十條為新表。
  - Given 夾具常數表 `GUARD_ARMS_V16`（九個表名→允許欄陣列，抄自 `V16__research_core.sql:67-81`）；以 `pg_get_functiondef('console.research_controlled_update_guard'::regproc)` 取現行本體
  - When 解析 `CASE TG_TABLE_NAME` 的 `WHEN … THEN ARRAY[…]` 條目
  - Then 條目恰十條：前九條與常數表逐條逐欄相等（含順序）、第十條為 `research_watch_sources`→`enabled`、`disabled_by`、`disabled_at`；函式其餘敘述（`DELETE` 擋、`allowed IS NULL` 擋、`to_jsonb` 差集比較）與 V16 本體一致；同類別另跑既有 `ResearchSchemaMigrationIT.AT_960_1_E_6*` 與 `AT_961_1_8*`（指令列兩個類別皆綠）
  - 判定：`gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchWatchSourceSchemaIT.AT_965_1_6*" --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_960_1_E_6*" --tests "com.aisdlc.console.infrastructure.persistence.ResearchSchemaMigrationIT.AT_961_1_8*"`；預期突變：重定義時漏抄任一既有條目、改動任一允許欄、把新表條目寫成含 `url`，皆紅
  - 驗收字樣：[AT_OK_965_1_6]
- **AT-965-1-7**（JUnit｜`ResearchWatchSourceSchemaIT`｜Integration｜AC-965-1、W-R1；AC-R2P-24-1）`url` CHECK 逐列等於根層附錄 D 的 CON 欄（D-EQA-1）。
  - Given 附錄 D 複本 `appendix-d.txt`（先重算複本 sha256 等於 `25fd334dc97b8d135393849851962abfb54a621f11f9f0b1ba80eb27f4de1e89`，不符即紅）；空表（除種子外）
  - When 對附錄 D 的**每一列**以該 URL 直接 INSERT（其餘欄位填合法值、slug 以列序號衍生）；另加兩列長度：`https://x.com/` 加滿到 500 字元、501 字元
  - Then `CON=T` 的列全部寫入成功（含 `https://example.org` 無路徑、`…?q=1&r=%28a%29`、17 列種子 URL 含 arxiv 長 URL）；`CON=F` 的列全部被擋（含 `xn--` label、大寫 `XN--`、非 ASCII 與全形、`93.184.216.34` 與其他 IPv4 字面、任何方括號 IPv6、`localhost`、`app.localhost`、userinfo、`:8443`、`:80`、顯式 `:443`、尾點、`http`、大寫 host、`#`、空白；CHECK 違反為 SQLSTATE 23514）；500 字元通過、501 字元被擋（欄位長度的 22001）；DB 只做形狀粗篩以外**另有三條 CHECK**（拒 `xn--` label、拒 `localhost`／`*.localhost`、拒 IPv4 字面），使 DB 判定與 Bridge 的 CON 判定在附錄 D 逐列一致
  - 判定：`gradlew test --tests "com.aisdlc.console.infrastructure.persistence.ResearchWatchSourceSchemaIT.AT_965_1_7*"`；預期突變：拿掉三條附加 CHECK 之一、正規式放寬到允許埠／userinfo／大寫，皆至少一列紅
  - 驗收字樣：[AT_OK_965_1_7]
- **AT-965-1-E-1**（JUnit｜`BackupJobMigrationIT` 與 `ResearchWatchSourceSchemaIT`｜Integration｜AC-965-1、NFR-RR-5；AC-R2P-24-1）新表不破壞既有表升級快照；既有十八張 `research_` 表的守衛行為不退步。
  - Given 自 V14 升級到最新版的庫
  - When 跑既有 `BackupJobMigrationIT` 的 `snapshotOfExistingTables` 前後快照斷言（其查詢以 `research\\_%` 排除 research 表，新表自動涵蓋）；對新表以外的十八張表跑既有逐表 DELETE 擋（同 AT-961-1-E-1 的迴圈，表清單常數不含新表）
  - Then 前後快照相等；十八張表 DELETE 一律被擋、SQLSTATE 類別 23
  - 判定：`gradlew test --tests "com.aisdlc.console.infrastructure.persistence.BackupJobMigrationIT" --tests "com.aisdlc.console.infrastructure.persistence.ResearchWatchSourceSchemaIT.AT_965_1_E_1*"`；預期突變：新表若命名脫離 `research_` 前綴，`BackupJobMigrationIT` 快照紅
  - 驗收字樣：[AT_OK_965_1_E_1]
- **AT-965-2-1**（JUnit｜`SiConsoleWritesMigrationIT` 的新案 `AT_965_2_1…`｜Integration｜AC-965-2、W-R2；AC-R2P-24-2）kind CHECK 恰六值、約束名與欄寬不變。
  - Given 遷移至最新版
  - When 現查 `kind` 欄上的 CHECK 與 `character_maximum_length`
  - Then 恰一條 kind 的 CHECK、約束名 `si_console_writes_kind_check` 不變、定義含六個值（`decide`、`obs-add`、`obs-close`、`sched-set`、`run-request`、`src-registry`）；欄寬為 12；六值的最大字元長度（`src-registry`＝12）≤欄寬（防日後新增超長 kind 的靜默截斷／失敗：本斷言以 `max(length(kind))` 對欄寬）；INSERT `bogus`、`src-registry-x`（13 字元）、`SRC-REGISTRY` 皆被拒
  - 判定：`gradlew test --tests "com.aisdlc.console.infrastructure.persistence.SiConsoleWritesMigrationIT.AT_965_2_1*"`；預期突變：欄寬縮為 11、CHECK 漏 `src-registry`、V25 重建 CHECK 改名，皆紅
  - 驗收字樣：[AT_OK_965_2_1]
- **AT-965-2-2**（JUnit｜`SiConsoleWritesMigrationIT`｜Integration｜AC-965-2、W-R2；AC-R2P-24-2）`src-registry` 列可寫入，列不可改的觸發器不變。
  - Given 最新版庫
  - When INSERT 一列 `kind='src-registry'`（`subject_id` NULL、`digest='sha256:'+64 位十六進位'`、body 為含 `registry_text` 的 JSON 文字）；對它 `UPDATE kind`／`digest`／`body`；`UPDATE subject_id`（NULL→值）；`DELETE`
  - Then INSERT 成功；kind／digest／body 的 UPDATE 被拒且訊息含「不可改」；`subject_id` 由 NULL 填值允許（沿 V13 規則）；DELETE 允許（補償路徑）；`digest` 為 72 字元被欄寬擋
  - 判定：`gradlew test --tests "com.aisdlc.console.infrastructure.persistence.SiConsoleWritesMigrationIT.AT_965_2_2*"`；預期突變：V25 順手改了觸發器、放寬 digest 欄寬，皆紅
  - 驗收字樣：[AT_OK_965_2_2]
- **AT-965-2-3**（JUnit｜`SiConsoleWritesMigrationIT`｜Integration｜AC-965-2、W-R2；AC-R2P-24-2）自 V23 升級：既有五種列逐列不變。
  - Given 以 Flyway 目標版本 23 建庫並 INSERT 五種 kind 各一列
  - When 遷移到最新版
  - Then 五列的 `audit_ref||kind||body||key_id||mac` 串接內容與升級前逐列相同；歷史表最後兩版為 24、25 且 `success` 皆真；再跑一次 `migrationsExecuted` 為 0
  - 判定：`gradlew test --tests "com.aisdlc.console.infrastructure.persistence.SiConsoleWritesMigrationIT.AT_965_2_3*"`；預期突變：V25 以 `DELETE` 重建表，皆紅
  - 驗收字樣：[AT_OK_965_2_3]

**B. Bridge（pytest；真 PG 夾具 `RDB`）**

- **AT-965-3-1**（pytest｜`test_research_watch_sources.py`｜Integration｜AC-965-3、W-R3；AC-R2P-24-3）POST 正控：形狀、轉傳身分、事件帳與稽核面。
  - Given `LB` 加 `RDB`（含 V24 種子）、寫入權杖正確；`ENV` 基底含 `export.arxiv.org`；種子網域含 `www.anthropic.com`
  - When POST `{slug:"t-new-1", url:"https://www.anthropic.com/news", kind:"blog", extract:"最新 3 篇標題", layer:"INDUSTRY", expand:{mode:"links", prefix:"/news/", max:2}, added_by:"admin"}`
  - Then 201 且本文恰 `slug`、`url`、`host`（`www.anthropic.com`）、`kind`、`extract`、`layer`、`expand`（物件三鍵）、`enabled`（真）、`host_allowed`（真）、`added_by`（`admin`）、`added_at`（UTC `+00:00`、秒精度）、`disabled_by`／`disabled_at`（null）；DB 多恰一列；`research_events` 列數不變；`bridge.audit` 多恰一筆 `research_write{verb:"watch.add",approver:"admin",result:"ok"}` 且不含權杖
  - 判定：`python -m pytest tests/test_research_watch_sources.py -k AT_965_3_1 -q`；預期突變：POST 寫了 `research_events`、`added_by` 取請求本文以外的值、回應缺 `host_allowed`，皆紅
  - 驗收字樣：[AT_OK_965_3_1]
- **AT-965-3-2**（pytest｜`test_research_watch_sources.py`｜Integration｜AC-965-3、W-R3、NFR-RR-1；AC-R2P-24-3）六條輸入閘規則一次全列，零寫入。
  - Given 同 AT-965-3-1
  - When POST 一個**六個欄位各自違規**的本文（`slug:"-Bad"`、`url:"http://x"`、`kind:"rss"`、`extract:""`、`layer:"X"`、`expand:{mode:"links",prefix:"a",max:9}`）；另對 `expand` 缺 `max`、多一鍵 `extra`、`extract` 含換行、`slug` 33 字元、`slug` 32 字元（合法）各一案；本文多一個未知鍵
  - Then 422 `invalid_request`、`violations[]` 一次全列且每項含 `field`、`rule`、`message`（規則名∈`invalid_slug`／`invalid_url`／`invalid_kind`／`invalid_layer`／`invalid_extract`／`invalid_expand`）；六欄案恰六筆各一；33 字元 slug 違規、32 字元通過；未知鍵 422；任何一案 DB 零新增、`bridge.audit` 記 `result` 為 `rejected:…`
  - 判定：`python -m pytest tests/test_research_watch_sources.py -k AT_965_3_2 -q`；預期突變：只回第一筆違規、規則名改名、漏判 `expand` 缺鍵，皆紅
  - 驗收字樣：[AT_OK_965_3_2]
- **AT-965-3-3**（pytest｜`test_research_watch_sources.py`｜Unit｜AC-965-3、W-R3；AC-R2P-24-3）`check_watch_url` 原樣判定，逐列等於根層附錄 D 的 CON 欄（D-EQA-1）。
  - Given 純函式 `app.research.registry.check_watch_url(url) -> str | None`（None＝接受、否則規則名；**不做任何正規化**：大寫 host、顯式 `:443` 一律拒絕，由使用者自行改寫）與附錄 D 複本 `appendix-d.txt`（先重算複本 sha256 等於 `25fd334dc97b8d135393849851962abfb54a621f11f9f0b1ba80eb27f4de1e89`，不符即紅）
  - When 逐列呼叫（附錄 D 全部列，含 17 列種子 URL）
  - Then 每列判定（接受／拒絕）逐列等於 CON 欄：`CON=F` 全拒（規則名一律 `invalid_url`）、`CON=T` 全收；Bridge 拒絕集合包含 IDNA／`xn--` 任一 label（含大寫 `XN--`）、任何非 ASCII 字元（含全形數字與 `。`）、任何 IP 字面（IPv4、方括號 IPv6，即使是公網位址如 `93.184.216.34`）、`localhost`、`*.localhost`、userinfo、非 443 與顯式 `:443`、尾點、非 https、大寫 host、`#`、空白與控制字元、長度＞500；**逐列斷言 Console 接受集合 ⊆ SI 接受集合**：對 SI 欄為 `F` 的列 Console 必為 `F`（以表內 SI 欄直接斷言，零 `CON=T` 而 `SI=F` 的列）；函式純（同輸入同輸出、零 I/O）
  - 判定：`python -m pytest tests/test_research_watch_sources.py -k AT_965_3_3 -q`；預期突變：保留或改寫 `:443`、放行大寫 host、放行公網 IP 字面、不拒 `xn--`，皆至少一列紅
  - 驗收字樣：[AT_OK_965_3_3]
- **AT-965-3-4**（pytest｜`test_research_watch_sources.py`｜Integration｜AC-965-3、W-R3、D-170；AC-R2P-24-3）單一閘：host 必須在有效網域清單。
  - Given `ENV` 基底含 `export.arxiv.org`；ADMIN 條目：`www.anthropic.com`（FETCH，啟用）、`blog.example.com`（WEB，啟用）、`off.example.com`（FETCH，停用）
  - When POST 追蹤來源其 host 依序為 `export.arxiv.org`、`www.anthropic.com`、`blog.example.com`、`off.example.com`、`unknown.example.com`
  - Then 前三者 201（基底、FETCH、WEB 皆算有效）；後兩者 422 `host_not_allowed` 且 `details.host` 為該 host、DB 零新增；規則名判斷序為先 `invalid_request` 後 `host_not_allowed`（同時違規時只回 `invalid_request`）；`host_allowed` 對三個通過者皆為真
  - 判定：`python -m pytest tests/test_research_watch_sources.py -k AT_965_3_4 -q`；預期突變：只檢 FETCH 不檢 WEB、把停用條目算有效、不檢 `ENV`，皆紅
  - 驗收字樣：[AT_OK_965_3_4]
- **AT-965-3-5**（pytest｜`test_research_watch_sources.py`｜Integration｜AC-965-3、W-R3；AC-R2P-24-3）slug 重複 409，slug 永不重用。
  - Given 種子列 `cc-releases`（啟用）；一列新建後被停用的 `t-gone`
  - When POST 同 slug `cc-releases`；POST 同 slug `t-gone`；列出所有 HTTP 方法對 `/research/watch-sources/{slug}` 的路由
  - Then 兩者皆 409 `watch_source_exists` 且 `details.slug` 為該 slug、DB 零新增；路由表沒有 DELETE（對 `/research/watch-sources/t-gone` 發 DELETE 得 405）
  - 判定：`python -m pytest tests/test_research_watch_sources.py -k AT_965_3_5 -q`；預期突變：停用後允許以同 slug 重建、加了 DELETE 路由，皆紅
  - 驗收字樣：[AT_OK_965_3_5]
- **AT-965-3-6**（pytest｜`test_research_watch_sources.py`｜Integration｜AC-965-3、W-R3；AC-R2P-24-3）PATCH：只收 `enabled`；停用須 `disabled_by`；重新啟用清空停用欄並檢 host。
  - Given 一列啟用的 `t-a`（host `www.anthropic.com`）
  - When PATCH `{enabled:false}`（缺 `disabled_by`）；`{enabled:false, disabled_by:"admin"}`；`{enabled:false, url:"https://x"}`（多鍵）；`{enabled:true}`；先停用網域 `www.anthropic.com` 後再 PATCH `{enabled:true}`；PATCH 不存在的 slug；非法 slug 形態
  - Then 缺 `disabled_by` 422；第二案 200 且 `enabled=false`、`disabled_by="admin"`、`disabled_at` 為 UTC 秒精度；多鍵 422；第四案 200 且 `disabled_by`、`disabled_at` 為 null、其餘欄位與停用前逐值相同；網域已停用時重新啟用 422 `host_not_allowed`；不存在的 slug 404 `research_not_found`（`details.slug`）；非法 slug 404；全程 `research_events` 不變
  - 判定：`python -m pytest tests/test_research_watch_sources.py -k AT_965_3_6 -q`；預期突變：重新啟用後 `disabled_*` 殘留、可改 `url`、重新啟用不檢 host，皆紅
  - 驗收字樣：[AT_OK_965_3_6]
- **AT-965-3-7**（pytest｜`test_research_watch_sources.py`｜Integration｜AC-965-3、W-R3、D-170；AC-R2P-24-3）停用網域後追蹤來源列不動、`host_allowed` 轉假。
  - Given 三列啟用的追蹤來源在 `www.anthropic.com` 下
  - When 經既有 `PATCH /research/allowlist/{id}` 停用該網域條目；`GET /research/watch-sources`；再重新啟用該網域條目；再 GET
  - Then 停用後三列 `enabled` 仍為真、`host_allowed` 為假；重新啟用後 `host_allowed` 為真；追蹤來源表零 UPDATE（逐列快照相等）
  - 判定：`python -m pytest tests/test_research_watch_sources.py -k AT_965_3_7 -q`；預期突變：停用網域時連帶改寫追蹤來源列，皆紅
  - 驗收字樣：[AT_OK_965_3_7]
- **AT-965-3-8**（pytest｜`test_research_watch_sources.py`｜Integration｜AC-965-3、W-R3；AC-R2P-24-3）大小閘邊界。
  - Given 夾具把表填到「再新增一列的快照恰為 24576 位元組」與「恰為 24577 位元組」兩個狀態（以調整 `extract` 長度逼近，並以 `registry_text` 實算位元組確認；多位元組字元算位元組不算字元）
  - When POST 該列
  - Then 恰 24576 通過（201）、24577 被拒 422 `registry_too_large`（`details.what="registry_text"`、`details.limit=24576`、`details.size=24577`）且 DB 零新增；常數 `REGISTRY_TEXT_MAX_BYTES` 只在 `app/research/registry.py` 定義一處
  - 判定：`python -m pytest tests/test_research_watch_sources.py -k AT_965_3_8 -q`；預期突變：以字元數而非位元組數計、上限寫成 24575、把檢查放在寫入之後，皆紅
  - 驗收字樣：[AT_OK_965_3_8]
- **AT-965-3-9**（pytest｜`test_research_watch_sources.py`｜Integration｜AC-965-3、W-R3；AC-R2P-24-3）讀端排序、無 DSN 與權杖。
  - Given 種子庫；另一個無 `BRIDGE_DB_DSN` 的 Bridge；寫入權杖缺／錯／未設
  - When GET 清單；無 DSN 時 GET／POST；POST 不帶權杖、帶錯權杖、Bridge 未設權杖
  - Then 清單 17 列（種子）依 `slug` 位元組序（`a-b` 排在 `a0` 之前或之後依 `COLLATE "C"`，以夾具 `["a-b","a0","aa"]` 驗位元組序）、含停用列；無 DSN 503 `research_requires_db`；缺或錯權杖 403 `research_write_forbidden`、未設 503 `research_write_disabled`（沿 §2.1）；GET 不需權杖
  - 判定：`python -m pytest tests/test_research_watch_sources.py -k AT_965_3_9 -q`；預期突變：以資料庫預設排序（非 C 序）、GET 要求權杖，皆紅
  - 驗收字樣：[AT_OK_965_3_9]
- **AT-965-3-E-1**（pytest｜`test_research_router.py`、`test_research_watch_sources.py`｜Integration｜AC-965-3、W-R0、NFR-RR-5；AC-R2P-24-3）R2P allowlist 端點的行為零變動。
  - Given 加入新端點後的 Bridge
  - When 跑既有 `test_research_router.py` 的 `AT_960_8_9*` 全部案例；另以同一 `RDB`（含種子）對 `GET／POST／PATCH /research/allowlist` 呼叫並與升級前的黃金回應形狀比對
  - Then 既有案例全綠（其斷言只因種子帶來的 `items` 增列而改預期值者列在 §4.1；回應鍵集合、狀態碼、`effective` 的組成算式不變）；`effective.FETCH` 在含種子的庫為部署基底加四個種子網域；新端點的存在不改變 `check_research_url` 與 `build_effective_allowlist` 的簽章（以 `inspect.signature` 對拍）
  - 判定：`python -m pytest tests/test_research_router.py -k AT_960_8_9 -q`；`python -m pytest tests/test_research_watch_sources.py -k AT_965_3_E_1 -q`；預期突變：改動 `build_effective_allowlist` 簽章，皆紅
  - 驗收字樣：[AT_OK_965_3_E_1]
- **AT-965-4-1**（pytest｜`test_research_registry_snapshot.py`｜Integration｜AC-965-4、W-R4、D-172；AC-R2P-24-4）黃金檔 G-R1（空登記）的位元組與 sha 逐位元相等。
  - Given `ENV` 基底只含 `export.arxiv.org`；G-R1 夾具庫（無 ADMIN 條目、無追蹤來源：使用只建表與守衛、不跑種子 INSERT 的 `RDB` 夾具；表不可 DELETE，故不以刪種子達成）；夾具檔 `golden-r1.json` 與 sha 常數
  - When `GET /research/registry`
  - Then `registry_text` 的 UTF-8 位元組與黃金檔逐位元組相等（205 位元組）、`registry_sha256` 為 `sha256:73123a2bf0275448928199a72895297c77d6af8773ffa14b7cf453d19dc393a3`；黃金檔本身的 sha 以 `hashlib` 於測試內重算再比（防夾具被手改）；含三列追蹤來源的情形由 AT-965-4-E-2（附錄 B）承擔
  - 判定：`python -m pytest tests/test_research_registry_snapshot.py -k AT_965_4_1 -q`；預期突變：改 `indent`、`sort_keys`、`ensure_ascii`、結尾換行、時間格式、`expand` 鍵序，皆紅
  - 驗收字樣：[AT_OK_965_4_1]
- **AT-965-4-2**（pytest｜`test_research_registry_snapshot.py`｜Integration｜AC-965-4、W-R4、NFR-RR-2；AC-R2P-24-4）同一 DB 狀態連呼兩次逐位元組相同；與插入順序無關。
  - Given 兩個庫：以兩種不同的插入順序（正序、逆序，含 ADMIN 網域與追蹤來源）建立同一份內容
  - When 各呼叫 `GET /research/registry` 兩次
  - Then 同庫兩次相同；兩庫的 `registry_text` 與 `registry_sha256` 相同；連呼 20 次零差異
  - 判定：`python -m pytest tests/test_research_registry_snapshot.py -k AT_965_4_2 -q`；預期突變：快照依資料庫回傳順序而不排序，皆紅
  - 驗收字樣：[AT_OK_965_4_2]
- **AT-965-4-3**（pytest｜`test_research_registry_snapshot.py`｜Unit｜AC-965-4、W-R4；AC-R2P-24-4）`hosts` 規則表驅動：只列啟用、(list_kind,host) 單次、ENV 優先、位元組序。
  - Given 純函式 `build_registry_hosts(env_fetch, env_web, admin_rows)` 與輸入表
  - When 逐列呼叫
  - Then 停用條目不列；同一 `(FETCH, host)` 在基底與 ADMIN 皆有→一筆 `source=ENV`、`layer=null`；同 host 同時在 FETCH 與 WEB→兩筆（依 `list_kind` 位元組序 `FETCH`＜`WEB`）；排序以 UTF-8 位元組序：`a-b.com`、`a.com`、`a0.com`、`B.com` 小寫化後的相對順序與 `sorted(key=bytes)` 一致（含 `-` 〔0x2D〕＜`.`〔0x2E〕＜數字＜字母）；`layer` 取 ADMIN 條目的值；host 一律小寫
  - 判定：`python -m pytest tests/test_research_registry_snapshot.py -k AT_965_4_3 -q`；預期突變：以區域排序（locale）、重複列出基底主機，皆紅
  - 驗收字樣：[AT_OK_965_4_3]
- **AT-965-4-4**（pytest｜`test_research_registry_snapshot.py`｜Unit｜AC-965-4、W-R4；AC-R2P-24-4）`min_interval_seconds` 算式。
  - Given 輸入表：基底 `api.github.com`、基底 `export.arxiv.org`、基底表外 `x.example`、ADMIN 條目 `www.anthropic.com` 值 5／1／3600、同 host 兩個 ADMIN 條目 FETCH 與 WEB（值 7 與 2）
  - When 計算
  - Then `api.github.com`＝60；`export.arxiv.org`＝3；`x.example`＝3；ADMIN 值 5→5、1→3（低於內建下限取下限）、3600→3600；同 host FETCH 與 WEB 各自以自己的條目值取 `max(builtin_floor, 值)`（FETCH＝7、WEB＝3）；FETCH 的結果等於 `EffectiveAllowlist.interval(host)`（以同一輸入建 `build_effective_allowlist` 對拍）
  - 判定：`python -m pytest tests/test_research_registry_snapshot.py -k AT_965_4_4 -q`；預期突變：直接用條目值不取下限、GitHub 取 1，皆紅
  - 驗收字樣：[AT_OK_965_4_4]
- **AT-965-4-5**（pytest｜`test_research_registry_snapshot.py`｜Integration｜AC-965-4、W-R4；AC-R2P-24-4）`watch` 全列、時間與 `expand` 形狀。
  - Given 庫內：一列啟用帶 `expand`、一列停用、一列「停用後重新啟用」、一列 `added_at` 帶微秒與非 UTC 偏移（以 SQL 寫入 `+08:00` 與 `.123456`）
  - When 取快照並解析
  - Then `watch` 含全部四列（含停用）依 `id` 位元組序；每個元素鍵集合恰十一鍵；`expand` 為 null 或恰 `{max,mode,prefix}` 三鍵；時間字串皆 `YYYY-MM-DDTHH:MM:SS+00:00`（微秒截斷、偏移換算成 UTC）；重新啟用列的 `disabled_by`、`disabled_at` 為 null 且與從未停用的同形列內容一致；`enabled` 為 JSON 布林
  - 判定：`python -m pytest tests/test_research_registry_snapshot.py -k AT_965_4_5 -q`；預期突變：輸出本地時區、保留微秒、`enabled` 輸出為字串，皆紅
  - 驗收字樣：[AT_OK_965_4_5]
- **AT-965-4-6**（pytest｜`test_research_registry_snapshot.py`｜Integration｜AC-965-4、W-R4、NFR-RR-2；AC-R2P-24-4）停用／重新啟用網域與 digest 往返。
  - Given 種子庫；記下 digest D0
  - When 停用 `github.com` 網域條目→取快照 D1；重新啟用→取快照 D2；停用一個追蹤來源→D3；重新啟用它→D4
  - Then `hosts` 在 D1 少 `github.com` 而 `watch` 全列不變；D2＝D0；D3≠D0、`watch` 中該列 `enabled=false`；D4＝D0（重新啟用清空停用欄）；D0、D1、D3 兩兩相異
  - 判定：`python -m pytest tests/test_research_registry_snapshot.py -k AT_965_4_6 -q`；預期突變：重新啟用不清停用欄使 D4≠D0、停用網域時從 `watch` 移除列，皆紅
  - 驗收字樣：[AT_OK_965_4_6]
- **AT-965-4-7**（pytest｜`test_research_registry_snapshot.py`｜Unit｜AC-965-4、W-R4；AC-R2P-24-4）sha 公式與位元組衛生。
  - Given 任一快照
  - When 獨立以 `hashlib.sha256(text.encode("utf-8")).hexdigest()` 重算；檢視位元組
  - Then `registry_sha256` 為 `sha256:` 加該 64 位小寫十六進位；`registry_text` 以恰一個 `\n` 結尾、不含 `\r`、不含 BOM、非 ASCII 字元（種子中文 `extract`）原樣以 UTF-8 出現（不見 `\u` 跳脫）；`json.loads` 後鍵集合恰頂層三鍵；回應 JSON 恰兩鍵
  - 判定：`python -m pytest tests/test_research_registry_snapshot.py -k AT_965_4_7 -q`；預期突變：用 `ensure_ascii=True`、缺結尾換行、算 sha 時對 `str` 而非位元組，皆紅
  - 驗收字樣：[AT_OK_965_4_7]
- **AT-965-4-8**（pytest｜`test_research_registry_snapshot.py`｜Integration｜AC-965-4、W-R4；AC-R2P-24-4）超界與無 DSN。
  - Given 把常數以 `monkeypatch` 暫降到小於種子快照的值；無 DSN 的 Bridge
  - When GET registry
  - Then 422 `registry_too_large`（`details.what="registry_text"`、`limit`、`size`）；無 DSN 503 `research_requires_db`；不回部分內容
  - 判定：`python -m pytest tests/test_research_registry_snapshot.py -k AT_965_4_8 -q`；預期突變：超界時截斷後回 200，皆紅
  - 驗收字樣：[AT_OK_965_4_8]
- **AT-965-4-9**（pytest｜`test_research_registry_snapshot.py`｜Unit｜AC-965-4、NFR-RR-2；AC-R2P-24-4）快照路徑不讀時鐘（靜態）。
  - Given `app/research/registry.py` 原始碼與 `routers/research.py` 的 `get_registry` 函式（AST）
  - When 掃描對 `datetime.now`、`datetime.utcnow`、`time.time`、`time.monotonic`、`uuid` 產生、`random` 的呼叫
  - Then 零命中；掃描器有負控（對含 `datetime.now()` 的樣本回報）且範圍非空（至少掃到一個函式定義）
  - 判定：`python -m pytest tests/test_research_registry_snapshot.py -k AT_965_4_9 -q`；預期突變：快照加入 `generated_at`，皆紅
  - 驗收字樣：[AT_OK_965_4_9]
- **AT-965-4-E-1**（pytest｜`test_research_registry_snapshot.py`｜Unit｜AC-965-4、W-R4、D-EQA-3；AC-R2P-24-4）`is_public_ip` 對根層附錄 A 逐列相符。
  - Given 附錄 A 複本 `appendix-a.txt`（先重算複本 sha256 等於 `3101fd6aaebaf80e51d5161b3dee4ea87e8c9b15d2ac1a09f7c58ce55f230afd`，441 位元組，不符即紅）；`app.research.fetch.allowlist.is_public_ip`
  - When 逐行解析（`位址<TAB>T｜F`；含空字串列與 `not-an-ip`、`999.1.1.1`、`1.2.3`、帶 `%eth0` 的 scope id 列）並呼叫
  - Then 每列 `is_public_ip(位址)` 的布林等於 `T`／`F`（共 34 列，含空字串列）；解析不出的位址一律 `F`；表檔以 LF 結尾、列數與 `T` 數、`F` 數寫死比對（防夾具被截斷）
  - 判定：`python -m pytest tests/test_research_registry_snapshot.py -k AT_965_4_E_1 -q`；預期突變：改動 `is_public_ip` 的任一判準（例如放行 `100.64.0.1`、`198.51.100.1`、`::ffff:127.0.0.1`），皆至少一列紅
  - 驗收字樣：[AT_OK_965_4_E_1]
- **AT-965-4-E-2**（pytest｜`test_research_registry_snapshot.py`｜Integration｜AC-965-4、W-R4、D-EQA-3；AC-R2P-24-4）以根層附錄 B 的列內容為 DB 夾具，`GET /research/registry` 與附錄 B golden 逐位元組相同。
  - Given 附錄 B 複本 `appendix-b.json`（先重算複本 sha256 等於 `147fccd6a1b9efb61423579e26fbbc7437366a937806e239c69f334732aff0e8`，2039 位元組，不符即紅）；`RDB`（只建表與守衛、不跑種子）；`ENV` 基底只含 `export.arxiv.org`；測試自複本的 JSON 解析出列內容並寫入：ADMIN 條目（`www.anthropic.com`、FETCH、INDUSTRY、間隔 5）與三列追蹤來源（`anthropic-engineering` 停用、`anthropic-research` 帶 `expand`、`arxiv-agents`；`added_by`／`added_at`／`disabled_by`／`disabled_at` 逐列取附錄 B 的值，以 SQL 直寫固定時間）
  - When `GET /research/registry`
  - Then `registry_text` 的 UTF-8 位元組與附錄 B 逐位元組相等（2039 位元組）、`registry_sha256` 為 `sha256:147fccd6a1b9efb61423579e26fbbc7437366a937806e239c69f334732aff0e8`；`added_by` 與契約 §5A.1 種子表逐字一致（`anthropic-engineering` 為舊表匯入、`anthropic-research` 與 `arxiv-agents` 為單一化種子；D-EQA-18）
  - 判定：`python -m pytest tests/test_research_registry_snapshot.py -k AT_965_4_E_2 -q`；預期突變：改動 `indent`、鍵序、`min_interval_seconds` 算式、`expand` 物件鍵、時間格式、`added_by` 字面，皆紅
  - 驗收字樣：[AT_OK_965_4_E_2]

**C. console-api（JUnit；`AbstractApiIT` 加迷你 Bridge）**

- **AT-965-5-1**（JUnit｜`ResearchWatchSourceApiIT`、`RbacIT`｜Integration｜AC-965-5、W-R5、NFR-RR-1；AC-R2P-24-5）角色矩陣與零 Bridge 請求。
  - Given 三種角色憑證與迷你 Bridge
  - When 對 `GET /api/v1/research/watch-sources`、`POST` 同路徑、`PATCH /api/v1/research/watch-sources/{slug}` 各以匿名、VIEWER、OPERATOR、ADMIN 呼叫
  - Then 匿名 401；GET 三角色皆 200；POST／PATCH 在 VIEWER 與 OPERATOR 回 403 且 `reason` 為 `ACCESS_DENIED`、迷你 Bridge 的 watch 寫入請求數為 0、DB `research_watch_sources` 零變動；ADMIN 通過授權層（後續狀態碼依前置，不為 401 或 403）；兩條 matcher 置於通用 `/api/v1/**` 規則之前（以規則順序反射檢查與 OPERATOR 403 雙重佐證）
  - 判定：`gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchWatchSourceApiIT.AT_965_5_1*" --tests "com.aisdlc.console.infrastructure.security.RbacIT.AT_965_5_1*"`；預期突變：漏掉 PATCH matcher、matcher 排在通用規則之後，皆紅
  - 驗收字樣：[AT_OK_965_5_1]
- **AT-965-5-2**（JUnit｜`ResearchWatchSourceApiIT`｜Integration｜AC-965-5、W-R5；AC-R2P-24-5）ADMIN 寫入的審計與事件帳。
  - Given ADMIN、迷你 Bridge（成功回放 201／200）；前後的 `audit_log` 與 `research_events` 列數；`audit` logger 擷取
  - When ADMIN POST 一筆、PATCH 停用該筆；ADMIN POST 一筆被迷你 Bridge 回 422 `host_not_allowed`；OPERATOR POST（403）
  - Then 成功的兩次各使 `audit_log` 多恰一列：`entity_type='research_watch_source'`、`entity_id` 為該 slug、`subject` 為 JWT subject、`role` 為 ADMIN、`http_status` 依序 201 與 200、帶 trace_id、不含請求本文；`audit` 日誌行帶 `action=research.watch_source` 與 `entity=research_watch_source:<slug>`；被拒的 422 與 403 亦各多恰一列（`http_status` 為 422／403；沿 AT-960-5-4 的規則，V6 無 `note` 欄故不斷言）；全程 `research_events` 列數不變；轉給 Bridge 的 `added_by`／`disabled_by` 等於 JWT subject（迷你 Bridge 記錄）
  - 判定：`gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchWatchSourceApiIT.AT_965_5_2*"`；預期突變：寫 `research_events`、entity 標成 `research_allowlist`、請求本文可指定 `addedBy`，皆紅
  - 驗收字樣：[AT_OK_965_5_2]
- **AT-965-5-3**（JUnit｜`ResearchWatchSourceApiIT`｜Integration｜AC-965-5、W-R5、NFR-RR-1；AC-R2P-24-5）輸入閘 400 先於 Bridge。
  - Given ADMIN 與迷你 Bridge
  - When POST 逐欄違規（slug 33 字元、url 非 https、kind 列舉外、layer 列舉外、extract 空與 201 字、`expand` 缺鍵／`max` 為 4／`prefix` 無前導斜線、本文含 `addedBy` 鍵、本文非物件）
  - Then 各回 400 與 `errors[]`（逐欄 `field`、`message`）；迷你 Bridge 的 watch 寫入請求數為 0；`addedBy` 鍵被拒（400，規則 `unknown_field`），不被默默忽略
  - 判定：`gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchWatchSourceApiIT.AT_965_5_3*"`；預期突變：輸入閘缺一欄、默默忽略 `addedBy`，皆紅
  - 驗收字樣：[AT_OK_965_5_3]
- **AT-965-5-4**（JUnit｜`ResearchWatchSourceApiIT`｜Integration｜AC-965-5、W-R5；AC-R2P-24-5）Bridge 錯誤逐字透傳。
  - Given 迷你 Bridge 回放：409 `watch_source_exists`（`details.slug`）、422 `host_not_allowed`（`details.host`）、422 `registry_too_large`（`details`）、422 `invalid_request`（`violations`）、404 `research_not_found`、503 `research_requires_db`、403 `research_write_forbidden`、連線失敗、讀取逾時
  - When ADMIN 對應呼叫
  - Then 狀態碼、`reason`、`details` 逐字透傳（502 `bridge_unreachable`、504 `bridge_timeout` 沿 §0.2 第 8 列）；POST 不重試（迷你 Bridge 請求數恰 1）；`reason` 字串住 `ErrorReasons` 的 `REGISTRY_` 常數（三個新值）與既有常數
  - 判定：`gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchWatchSourceApiIT.AT_965_5_4*"`；預期突變：自行重試、改寫 reason，皆紅
  - 驗收字樣：[AT_OK_965_5_4]
- **AT-965-5-5**（JUnit｜`ResearchApiIT`｜Integration｜AC-965-5、W-R0、NFR-RR-5；AC-R2P-24-5）R2P 既有 allowlist 三端點的回應與 Bridge 請求數不變。
  - Given 與既有 AT-960-5-4 相同的夾具與步驟
  - When 重跑 `ResearchApiIT.AT_960_5_4*`；並在同一測試內加對照：GET allowlist、POST、PATCH 各一次，記迷你 Bridge 的請求計數
  - Then 既有 AT-960-5-4 全綠（預期值零改）；每個 allowlist 呼叫恰對應一次 Bridge 請求、不多出任何 `watch-sources` 或 `registry` 請求（逐路徑計數）；回應鍵集合與升級前相同
  - 判定：`gradlew test --tests "com.aisdlc.console.adapter.in.web.ResearchApiIT.AT_960_5_4*" --tests "com.aisdlc.console.adapter.in.web.ResearchApiIT.AT_965_5_5*"`；預期突變：allowlist 端點順帶呼叫新端點，皆紅
  - 驗收字樣：[AT_OK_965_5_5]
- **AT-965-5-6**（JUnit｜`OpenApiIT`｜Integration｜AC-965-5、W-R5；AC-R2P-24-5）OpenAPI：三個操作、DTO 必填鍵、失敗碼文件化。
  - Given `/v3/api-docs`
  - When 讀 `/api/v1/research/watch-sources` 與 `/{slug}` 路徑及 `WatchSourceDto` 結構描述
  - Then `operationId` 恰 `listResearchWatchSources`、`addResearchWatchSource`、`updateResearchWatchSource`；方法與路徑固定、無 DELETE；`WatchSourceDto` 的 `required` 含 `slug`、`url`、`host`、`kind`、`extract`、`layer`、`expand`（可空）、`enabled`、`hostAllowed`、`addedBy`、`addedAt`、`disabledBy`（可空）、`disabledAt`（可空）；POST 文件化 400／403／409／422／502／503／504、PATCH 文件化 400／403／404／422／502／503／504（409 只列 POST，PATCH 不撞 slug；勘誤 E-2）；GET 含 401 與 502／503／504；每個狀態碼說明非空
  - 判定：`gradlew test --tests "com.aisdlc.console.infrastructure.config.OpenApiIT.AT_965_5_6*"`；預期突變：加 DELETE、DTO 欄名 snake_case，皆紅
  - 驗收字樣：[AT_OK_965_5_6]
- **AT-965-5-E-1**（JUnit｜`ResearchArchTest`｜Unit｜AC-965-5、W-R5；AC-R2P-24-5）ArchUnit：呼叫面與零寫入掃描。
  - Given `backend/src/main` 的類別與原始碼
  - When 檢查 `ResearchBridge` 新四方法的呼叫者；字串掃描 `adapter.out.persistence.research` 套件與 `ResearchRegistryService` 對 `research_watch_sources` 的 `INSERT`／`UPDATE`／`DELETE`／`MERGE`／`TRUNCATE`
  - Then 新方法只被 `ResearchRegistryService` 與 `SiConsoleWriteService`（僅 `registry()` 讀取）呼叫；console-api 對 `research_watch_sources` 零寫入（讀取走 `JdbcClient`）；既有 `ResearchArchTest.AT_960_4_E_1*` 仍綠（掃描器涵蓋新類且有負控）
  - 判定：`gradlew test --tests "com.aisdlc.console.architecture.ResearchArchTest"`；預期突變：在 console-api 直接 INSERT 該表，皆紅
  - 驗收字樣：[AT_OK_965_5_E_1]
- **AT-965-6-1**（JUnit｜`SiRegistrySyncApiIT`、`SiAuditSignerTest`｜Integration｜AC-965-6、W-R6、D-172；AC-R2P-24-6）同步正控：簽章、原樣嵌入、落檔位元組。
  - Given `ADMIN`、`K0`、`Clock.fixed`、`SEAM` 排入一個 ref；`MINI.registry(text, sha)` 回放根層附錄 B golden（複本 `appendix-b.json`，2039 位元組、sha256 `147fccd6…f0e8`）的 `registry_text` 與 `registry_sha256`（含換行與非 ASCII）；`MINI.status` 的 `research_registry` 為 null、鏡像事件空
  - When `POST /api/v1/si/research-registry/sync`
  - Then 201、`outcome=written`、`state=pending`、收據含 `auditRef`、`kind="src-registry"`、`time`（`±HH:MM`、不含 `Z`）、`keyId`、`registrySha256`；`si_console_writes` 多恰一列（`kind=src-registry`、`user=admin`、`role=ADMIN`、`subject_id` 為 NULL、`digest`＝附錄 B golden 的 sha、`body` 為簽章 body 逐字）；`MINI.si.writes` 收到的位元組＝外層檔（恰七鍵、序固定 `schema_rev,kind,audit_ref,subject,body,key_id,mac`、`subject` 為 null、緊湊、無 BOM、結尾恰一個 LF〔以附錄 C 為準，勘誤 E-1〕）；解開外層 `body` 後的鍵序為 `schema_rev,audit_ref,kind,user,role,time,registry_text,registry_sha256`，且 `registry_text`、`registry_sha256` 兩欄的值與 `MINI.registry` 回放逐位元組相同（含 `\n`、中文、引號）；`mac` 以 `K0` 對 body 位元組重算相等；收據與回應文案不含「已同步」「已生效」字樣
  - 判定：`gradlew test --tests "com.aisdlc.console.adapter.in.web.SiRegistrySyncApiIT.AT_965_6_1*" --tests "com.aisdlc.console.application.service.SiAuditSignerTest"`；預期突變：console-api 重新序列化 `registry_text`、body 鍵序對調、`subject` 填值、digest 欄存成不含前綴，皆紅
  - 驗收字樣：[AT_OK_965_6_1]
- **AT-965-6-2**（JUnit｜`SiRegistrySyncApiIT`｜Integration｜AC-965-6、W-R6、NFR-RR-1；AC-R2P-24-6）閘門序表驅動；每關拒絕零副作用。
  - Given 表驅動夾具（每列：呼叫身分、設定、迷你 Bridge 行為；各列前後記 `rows()` 列數、`MINI.si.writes` 請求數、`refs` 取用次數）
  - When 逐列呼叫 sync：(1) OPERATOR；(2) `ADMIN2`（不在名單）；(3a) 金鑰未設；(3b) 權杖未設；(4a) 快照 503 `research_requires_db`；(4b) 快照連線失敗；(4c) 快照逾時；(4d) 快照 422 `registry_too_large`；(5) 鏡像讀取失敗；(5′) 鏡像掃描超上限；(6) 外層檔超界（見 AT-965-6-5 的夾具）
  - Then 狀態碼與 reason 依序：403 `ACCESS_DENIED`、403 `si_write_forbidden`、503 `si_write_disabled`（`details.cause` 為 `audit_key_unset`／`bridge_token_unset`）、503 `research_requires_db`、502 `bridge_unreachable`、504 `bridge_timeout`、422 `registry_too_large`（`what=registry_text`）、503 `si_unavailable`（`details.cause`）、503 `si_unavailable`（`scan_cap_exceeded`）、422 `registry_too_large`（`what=audit_file`）；每列 `rows()` 列數、`MINI.si.writes` 請求數、`refs` 取用次數變動量皆為 0；(1)～(3) 列另斷言迷你 Bridge 收到的 `GET /research/registry` 請求數為 0（序 4 尚未到）；先中者定案（同時違規只回較早一關）
  - 判定：`gradlew test --tests "com.aisdlc.console.adapter.in.web.SiRegistrySyncApiIT.AT_965_6_2*"`；預期突變：把取快照移到授權之前、鏡像失敗時仍寫入，皆紅
  - 驗收字樣：[AT_OK_965_6_2]
- **AT-965-6-3**（JUnit｜`SiRegistrySyncApiIT`｜Integration｜AC-965-6、W-R6；AC-R2P-24-6）冪等判定表。
  - Given 夾具：當前 digest `D`；鏡像事件 `research.registry` 列（seq 遞增，各帶 `registry_sha256` 與 `audit_ref`）；表內 `src-registry` 列（有的已入帳、有的未入帳；以 ref 是否在鏡像已入帳集合判斷）
  - When 逐列呼叫 sync（最新已入帳者＝`MINI.status` 的 `items[0].research_registry`，`{seq, audit_ref, registry_sha256, watch_enabled}`；已入帳 ref 集合＝`MINI.events` 的 `research.registry` 事件），列：(a) `research_registry.registry_sha256`＝`D`；(b) `research_registry.registry_sha256`≠`D`、有未入帳列 digest＝`D`；(c) `research_registry.registry_sha256`≠`D`、無相符未入帳列；(d) `research_registry` 為 `E`（最新）而事件序列含較舊的 `D`、當前為 `D`（A→B→A，舊 `D` 的列已入帳，不得被誤判為未入帳）；(e) 未入帳列 digest＝`E`≠`D`；(f) 從未同步（`research_registry` 為 null、事件空、表空）；(g) `research_registry` 缺鍵（根層未升版）
  - Then (a) 200 `outcome=unchanged`、`state=synced`、`auditRef` 為 `research_registry.audit_ref`；(b) 200 `unchanged`、`state=pending`、`auditRef` 為該未入帳列；(c) 201 `written`；(d) 201 `written`（最新已入帳是 `E`，當前 `D` 是新的同步事件）；(e) 201 `written`；(f) 201 `written`；(g) 503 `si_unavailable`（零副作用，缺鍵不當成從未同步）；(h) 另列：`research_registry.registry_sha256`＝`D`、表內有時間更晚的未入帳列 digest＝`E`（`P`＝E）、當前 `D` ⇒ **201 `written`**（D-EQA-7；即使當前＝`I`）；(i) 另列：`I`＝`D`、表內有時間**早於**最新已入帳列的未入帳列 digest＝`E`（根層會以 `REG-STALE` 拒收，不算 `P`）、當前 `D` ⇒ 200 `unchanged`、`synced`；(j) 另列：`P` 存在且 digest＝`D`（`I`＝`E`）⇒ 200 `unchanged`、`pending`；所有 `unchanged` 列零副作用（`rows()`、`MINI.si.writes`、`refs` 變動量為 0）；`unchanged` 時 `kind`、`time`、`keyId` 為 null
  - 判定：`gradlew test --tests "com.aisdlc.console.adapter.in.web.SiRegistrySyncApiIT.AT_965_6_3*"`；預期突變：比對「任一歷史事件」而非最新一筆、`pending` 列被忽略、有更新的待入帳寫入時仍以 `I` 判 `unchanged`、把更舊的未入帳列算成 `P`，皆紅
  - 驗收字樣：[AT_OK_965_6_3]
- **AT-965-6-9**（JUnit｜`SiRegistrySyncApiIT`｜Integration｜AC-965-6、W-R6、D-EQA-7；AC-R2P-24-6）端到端序列：D→E（待入帳）→D 照常送出新稽核檔。
  - Given 迷你 Bridge 與可程式化的鏡像替身（`MINI.status` 的 `research_registry`、`MINI.events` 可在步驟間改寫）；`Clock` 逐步前進；快照回放可切換內容 `D`、`E`
  - When 依序：(1) 鏡像已入帳 `D`（`research_registry.registry_sha256`＝`D`），當前 `D`，呼叫 sync；(2) 當前改 `E`，呼叫 sync（201，寫入列 R_E，**不入帳**）；(3) 當前改回 `D`，呼叫 sync；(4) 查 `GET /api/v1/si/research-registry`；(5) 再呼叫 sync；(6) 模擬巡邏依 `time` 順序入帳 R_E 再入帳 R_D2（鏡像 `research_registry` 先為 `E` 後為 `D`），查狀態並再呼叫 sync
  - Then (1) 200 `unchanged`、`synced`（零副作用）；(2) 201 `written`、`state=pending`；(3) **201 `written`**（有更新的待入帳寫入 `E`，當前 `D`≠`P.digest`，不得回 `unchanged`）、新列 R_D2 的 `time` 晚於 R_E；(4) 狀態 `pending`（`P`＝R_D2、`P.digest`＝當前）；(5) 200 `unchanged`、`pending`、`auditRef`＝R_D2（零副作用）；(6) 兩次入帳後狀態 `synced`、再呼叫 sync 為 200 `unchanged`、`synced`；全程表內 `src-registry` 列恰 R_E 與 R_D2 兩列、R_D2 的 `time` 嚴格大於 R_E（根層 `REG-STALE` 單調性的前提）
  - 判定：`gradlew test --tests "com.aisdlc.console.adapter.in.web.SiRegistrySyncApiIT.AT_965_6_9*"`；預期突變：步驟 (3) 以 `I` 判 `unchanged`（E 入帳後鏡像停在 E）、步驟 (4) 判 `synced`，皆紅
  - 驗收字樣：[AT_OK_965_6_9]
- **AT-965-6-4**（JUnit｜`SiRegistrySyncApiIT`｜Integration｜AC-965-6、W-R6；AC-R2P-24-6）補償與結果不明（沿 P2b 語意）。
  - Given `MINI.si` 對落檔請求回放：400／422、503、500、連線在連線階段失敗、讀取逾時、送出後連線重設、2xx 但本文非 JSON
  - When 各案呼叫 sync
  - Then 前四案：稽核列被補償刪除（表內無該 ref）、回應狀態碼對映同 P2b（Bridge 明確拒絕＝沿 `SiBridgeErrors.mapWrite`；5xx／連線階段＝502）；後三案：稽核列保留、錯誤 `details.outcomeUnknown` 為真、狀態碼 504／502；保留列使 AT-965-7-1 的 `pending` 判定成立；每案 Bridge 落檔請求數恰 1（不重試）
  - 判定：`gradlew test --tests "com.aisdlc.console.adapter.in.web.SiRegistrySyncApiIT.AT_965_6_4*"`；預期突變：逾時也補償刪除、自動重試，皆紅
  - 驗收字樣：[AT_OK_965_6_4]
- **AT-965-6-5**（JUnit｜`SiRegistrySyncApiIT`｜Integration｜AC-965-6、W-R6、NFR-RR-1；AC-R2P-24-6）外層檔超界：以位元組數現算，零副作用。
  - Given `MINI.registry` 回放一份 `registry_text`：UTF-8 位元組數＜24576 但幾乎全由雙引號與換行構成（跳脫後外層檔 >65536）；另一份典型內容（外層檔≤65536）
  - When 各呼叫 sync
  - Then 前者 422 `registry_too_large`（`details.what="audit_file"`、`size`＞65536、`limit=65536`）、`refs` 取用 0、表內列數不變、`MINI.si.writes` 為 0；後者 201；判定以簽章後外層檔的位元組數，而不是 `registry_text` 長度的估計（兩份夾具佐證估計不可行）
  - 判定：`gradlew test --tests "com.aisdlc.console.adapter.in.web.SiRegistrySyncApiIT.AT_965_6_5*"`；預期突變：只檢 `registry_text` 長度，皆紅
  - 驗收字樣：[AT_OK_965_6_5]
- **AT-965-6-6**（pytest｜`test_si_registry_route.py`｜Integration｜AC-965-6、W-R6；AC-R2P-24-6）Bridge `POST /si/registry:sync` 落檔。
  - Given `LB` 與 `BRIDGE_SI_AUDIT_DIR` 臨時目錄、`BRIDGE_SI_WRITE_TOKEN` 正確
  - When 送合法外層檔（`kind=src-registry`、`subject=null`、七鍵、`audit_ref` 小寫 UUID）；另送：`kind=decide`、`subject="x"`、缺鍵、多鍵、`audit_ref` 大寫、本文 65537 位元組、非 JSON、無權杖、錯權杖；沿既有檔名安全案例
  - Then 合法者 201 `{audit_ref, stored:true}`、`<audit_ref>.json` 位元組＝請求本文、檔案權限與既有三路由同；其餘各依既有規則 422／403／503（`kind_mismatch`、`subject` 非 null 的違規、`too_large` 等）；Bridge 不解讀 `body`（以 `body` 內放非 JSON 字串仍 201 驗證）；`bridge.audit` 多一筆 `si_write{verb:"registry-sync"}`
  - 判定：`python -m pytest tests/test_si_registry_route.py -k AT_965_6_6 -q`；預期突變：Bridge 解析並改寫 body、放寬 `kind` 檢查，皆紅
  - 驗收字樣：[AT_OK_965_6_6]
- **AT-965-6-7**（JUnit 與 pytest｜`SiAuditSignerTest`、`test_si_console_ingest.py`｜Integration｜AC-965-6、W-R6；AC-R2P-24-6）G-S1：Console 副本＝根層檔，Java 以附錄 C 同一組輸入重新產生，位元組相等（D-EQA-2、D-RR-17）。
  - Given 根層黃金檔 `tools/tests/fixtures/selfimproving/G-S1.audit.json`（**由根層實作輪先產出並提交**，依根層附錄 C〔1681 位元組、sha256 `91f13738…1d87`〕的固定輸入：金鑰 `si-test-key-g-s1-0123456789abcdef`、`audit_ref` `00000000-0000-4000-8000-0000000000a1`、`user` `admin`、`role` `ADMIN`、`time` `2026-11-10T09:00:00+08:00`、`registry_text`＝附錄 B golden）；**Console 副本路徑固定** `AgentConsole/backend/src/test/resources/si/G-S1.audit.json`（主控原樣複製；根層 AT-645-1-8 只驗根層檔對附錄 C，不讀本路徑——QA2-01：提交順序根層先、Console 後，副本一致性由本 AT 負責）；Bridge 副本 `AgentConsole/engine-bridge/tests/fixtures/si_audit/G-S1.audit.json`（同一份位元組）；**Console 不自產 G-S1，本 TCS 不預填其位元組**
  - When backend 的 `SiAuditSigner` 以上述同一組輸入（`Clock.fixed` 於 `2026-11-10T09:00:00+08:00`、`K0`＝上列金鑰、固定 ref、帳號 admin、`registry_text` 與 `registry_sha256` 取自附錄 B 複本）重新產生 body 與外層檔；Bridge 測試讀副本並以 Python 重算 HMAC 與 `sha256(registry_text)`
  - Then Java 產生的外層檔位元組與 backend 副本逐位元組相等（含外層鍵序 `schema_rev,kind,audit_ref,subject,body,key_id,mac`、body 鍵序 `schema_rev,audit_ref,kind,user,role,time,registry_text,registry_sha256`、緊湊分隔、非 ASCII 不跳脫、`/` 不跳脫、結尾恰一個 LF）；Python 端對 body 位元組重算的 `mac` 與檔內 `mac` 相等、`sha256(registry_text)` 等於 `registry_sha256`；兩副本與（主控提供的）根層檔 sha256 相等；副本不存在時**測試失敗**（不得 skip，依賴序見〈提交順序與責任〉）
  - 判定：`gradlew test --tests "com.aisdlc.console.application.service.SiAuditSignerTest.AT_965_6_7*"`；`python -m pytest tests/test_si_console_ingest.py -k AT_965_6_7 -q`；預期突變：Java 與 Python 任一側改鍵序或跳脫策略，皆紅
  - 驗收字樣：[AT_OK_965_6_7]
- **AT-965-6-8**（JUnit｜`SiRegistrySyncApiIT`｜Integration｜AC-965-6、W-R6、NFR-RR-6；AC-R2P-24-6）機密不外洩。
  - Given 簽章金鑰 `K0` 與寫入權杖的值（哨兵字串）；成功與各失敗案例；`LogCaptor`
  - When 跑 AT-965-6-1～6-5 的代表案例
  - Then 回應本文、錯誤 `details`、日誌、`rows()` 內任何欄位、迷你 Bridge 收到的請求標頭（除 `X-Bridge-Token` 本身須為正確值外）皆不含金鑰值；日誌只記 `kind`、`auditRef`、帳號名與 `key_id`；`X-Bridge-Token` 值不出現在日誌
  - 判定：`gradlew test --tests "com.aisdlc.console.adapter.in.web.SiRegistrySyncApiIT.AT_965_6_8*"`；預期突變：日誌印出金鑰、錯誤 `details` 帶權杖，皆紅
  - 驗收字樣：[AT_OK_965_6_8]
- **AT-965-6-E-1**（JUnit｜`SiReadOnlyArchTest`、`ResearchArchTest`｜Unit｜AC-965-6、W-R6；AC-R2P-24-6）ArchUnit：`siWriteRegistrySync` 唯一呼叫面；唯讀鎖不退步。
  - Given `backend/src/main` 類別
  - When 檢查 `AgentBridge.siWriteRegistrySync` 與 `SiConsoleWriteRepository` 的呼叫者；`SiReadOnlyArchTest` 既有規則
  - Then 兩者只被 `SiConsoleWriteService` 呼叫；既有唯讀鎖全綠；`SiController` 的新兩方法只依賴用例介面、不直接依賴 Bridge 或 repository
  - 判定：`gradlew test --tests "com.aisdlc.console.architecture.SiReadOnlyArchTest"`；預期突變：在別的 service 呼叫 `siWriteRegistrySync`，皆紅
  - 驗收字樣：[AT_OK_965_6_E_1]
- **AT-965-7-1**（JUnit｜`SiRegistryStatusApiIT`｜Integration｜AC-965-7、W-R7；AC-R2P-24-7）四態判定表。
  - Given `MINI.registry` 給當前 digest `D`；`MINI.status` 的 `items[0].research_registry`（`{seq, audit_ref, registry_sha256, watch_enabled}` 或 null）、`MINI.events`（`research.registry` 事件，供已入帳 ref 集合）與表內列依列組合
  - When `GET /api/v1/si/research-registry`，列：(a) `research_registry.registry_sha256`＝`D`；(b) `research_registry.registry_sha256`≠`D`、未入帳列 digest＝`D`；(c) `research_registry.registry_sha256`≠`D`、無相符列；(d) `research_registry` 為 null、事件空、表空；(e) `research_registry.registry_sha256`＝`D` 且同時有較新的未入帳列 digest＝`D`（重複寫入）；(h) `research_registry.registry_sha256`＝`D` 且有較新的未入帳列 digest＝`E`（D→E〔待入帳〕→D 的當下）；(i) `research_registry.registry_sha256`＝`D` 且未入帳列 digest＝`E` 但其 `time` 早於最新已入帳列（`REG-STALE` 會拒收，不算待入帳寫入）；(f) `research_registry.registry_sha256`＝`E`≠`D`、表內有 digest＝`D` 且 `audit_ref` 在事件已入帳集合內的舊列（A→B→A 的舊 A，不得判為 `pending`）；(g) `research_registry` 缺鍵
  - Then (a) `synced`；(b) `pending`（`pendingAuditRef`、`pendingTime` 為該列）；(c) `unsynced`；(d) `unsynced` 且 `ingestedSha256` 為 null；(e) `pending`（有 `P` 且 `P.digest`＝當前）；(h) `unsynced`（有 `P`、`P.digest`≠當前；**不得為 `synced`**，D-EQA-7）；(i) `synced`（更舊的未入帳列不算 `P`）；(f) `unsynced`；(g) 200、`state=unknown`、`unknownCause=si_unavailable`（缺鍵不當成從未同步）；`currentSha256` 恆為 `D`；多個未入帳列相符時取 `time` 最新者
  - 判定：`gradlew test --tests "com.aisdlc.console.adapter.in.web.SiRegistryStatusApiIT.AT_965_7_1*"`；預期突變：改取事件而非 `research_registry` 的最新者、把已入帳舊列判成 `pending`、有 `P` 時仍以鏡像 digest 判 `synced`、把更舊的未入帳列算成 `P`，皆紅
  - 驗收字樣：[AT_OK_965_7_1]
- **AT-965-7-2**（JUnit｜`SiRegistryStatusApiIT`｜Integration｜AC-965-7、W-R7、NFR-RR-4；AC-R2P-24-7）`unknown` 原因與主資料失敗。
  - Given 鏡像讀取（`GET /si/status` 取 `research_registry`、`GET /si/events` 掃已入帳 ref 集合）任一失敗：SI 不可用、掃描超上限、Bridge 不可達、逾時；另 `GET /research/registry` 自身失敗（502／503／504）
  - When GET 狀態
  - Then 鏡像類失敗＝200、`state=unknown`、`unknownCause` 依序 `si_unavailable`、`scan_cap_exceeded`、`bridge_unreachable`、`bridge_timeout`，`ingestedSha256` 等欄為 null，**不為 `synced`**；快照自身失敗＝非 200（502／503／504，沿 §0.2），不降級成 `unknown`
  - 判定：`gradlew test --tests "com.aisdlc.console.adapter.in.web.SiRegistryStatusApiIT.AT_965_7_2*"`；預期突變：讀不到時回 `synced` 或 `unsynced`，皆紅
  - 驗收字樣：[AT_OK_965_7_2]
- **AT-965-7-3**（JUnit｜`SiRegistryStatusApiIT`｜Integration｜AC-965-7、NFR-RR-6；AC-R2P-24-7）回應鍵集合與角色。
  - Given 三種角色
  - When GET 狀態；讀 OpenAPI `ResearchRegistrySyncStatus`
  - Then 三角色皆 200（VIEWER 可讀）；回應 `data` 的鍵集合恰 `state`、`unknownCause`、`currentSha256`、`ingestedSha256`、`ingestedAuditRef`、`pendingAuditRef`、`pendingTime`、`researchFetchMax`；不含 `body`、`mac`、`keyId`、`registryText`；OpenAPI `required` 含全部八鍵（可空者標 nullable）；匿名 401
  - 判定：`gradlew test --tests "com.aisdlc.console.adapter.in.web.SiRegistryStatusApiIT.AT_965_7_3*"`；預期突變：多回 `registryText`，皆紅
  - 驗收字樣：[AT_OK_965_7_3]
- **AT-965-7-4**（JUnit｜`SiRegistryStatusApiIT`｜Integration｜AC-965-7、W-R7、NFR-RR-4；AC-R2P-24-7）`researchFetchMax` 只轉鏡像值。
  - Given `MINI.status` 的 `items[0]` 依序：含 `research_fetch_max: 10`（整數，D-RR-15）、含 `research_fetch_max: 12`、缺鍵、為字串 `"10"`、為負數、為 0
  - When GET 狀態
  - Then 回 10、12、null、null、null、null（只有正整數才轉）；原始碼不含把 10 當預設值的常數（靜態掃描：`SiReconcileService`／狀態用例內無 `researchFetchMax` 的字面預設）；掃描有負控
  - 判定：`gradlew test --tests "com.aisdlc.console.adapter.in.web.SiRegistryStatusApiIT.AT_965_7_4*"`；預期突變：缺席時回 10，皆紅
  - 驗收字樣：[AT_OK_965_7_4]
- **AT-965-7-5**（JUnit｜`SiConsoleWritesReadApiIT`｜Integration｜AC-965-7、W-R7；AC-R2P-24-7）對帳讀面新 kind。
  - Given 表內一列 `src-registry`（已入帳／未入帳各一）；鏡像事件含 `research.registry`（carrier 為 console 與非 console 各一）
  - When `GET /api/v1/si/console-writes`
  - Then `items[].kind` 含 `src-registry`；已入帳者 `ingested=true`、未入帳者 `false`；carrier 為 console 且表內無對應列者出現在 `orphans`（kind `src-registry`、subject 為 null）；`SiWriteKind` 的 `wire()` 清單為六值（`OpenApiIT` 的對應斷言同步，§4.1）；既有五 kind 的對帳行為不變
  - 判定：`gradlew test --tests "com.aisdlc.console.adapter.in.web.SiConsoleWritesReadApiIT.AT_965_7_5*"`；預期突變：未對映 `research.registry`，皆紅
  - 驗收字樣：[AT_OK_965_7_5]

**D. frontend（vitest；jsdom；fetch 替身）**

- **AT-965-8-1**（vitest｜`lib/domain/researchRegistry.test.ts`｜Unit｜AC-965-8、W-R8；AC-R2P-24-8）純函式：表單驗證與請求本文。
  - Given `lib/domain/researchRegistry.ts` 的 `checkWatchUrl`（原樣判定、不正規化）、`watchSourceFormErrors`、`toWatchSourceRequest`，輸入表＝根層附錄 D 複本 `appendix-d.txt`（先重算複本 sha256 等於 `25fd334dc97b8d135393849851962abfb54a621f11f9f0b1ba80eb27f4de1e89`；與 AT-965-3-3 同一張表）另加 slug／kind／layer／extract／expand 案例
  - When 逐列呼叫
  - Then 前端 `checkWatchUrl` 對附錄 D 每一列的判定逐列等於 CON 欄（`CON=F` 拒、`CON=T` 收；大寫 host 與顯式 `:443` 拒絕且訊息指示使用者自行改寫，不自動改寫）；錯誤訊息逐欄第一則、無錯回空物件；`expand` 三欄「全空或全填」；`toWatchSourceRequest` 的鍵集合恰 `slug`、`url`（原樣送出）、`kind`、`extract`、`layer`、`expand`（無 `addedBy`）；slug 自動小寫建議不改使用者輸入
  - 判定：`npx vitest run lib/domain/researchRegistry.test.ts -t AT_965_8_1`；預期突變：前端放行 Bridge 拒絕的 URL（附錄 D 對拍紅）、前端自動小寫化或去掉 `:443`、請求本文帶 `addedBy`，皆紅
  - 驗收字樣：[AT_OK_965_8_1]
- **AT-965-8-2**（vitest｜`WatchSourcesSection.test.tsx`｜Integration｜AC-965-8、W-R8、NFR-RR-4；AC-R2P-24-8）清單渲染與警示。
  - Given `ADMIN_UI` 開對話框；`GET watch-sources` 回 17 列種子（10 啟用、7 停用）、其中一列 `hostAllowed:false`；狀態夾具 `researchFetchMax` 依序為 10、8、null
  - When 檢視追蹤來源區
  - Then 逐列顯示 slug、網址（純文字、可複製）、種類、層、展開設定（`links／sitemap`、prefix、max）、啟用狀態；停用列有「已停用」標示與「重新啟用」鈕、啟用列有「停用」鈕；`hostAllowed:false` 列顯示「網域未開放」並說明去上方網域清單開放；區頂顯示「啟用 10／共 17」；`researchFetchMax` 為 8 時顯示純文字警示「已超過自我進化每次抓取上限（8）」、為 10 與 null 時不顯示警示（null 時不出現任何數字上限字樣）
  - 判定：`npx vitest run components/domain/research/WatchSourcesSection.test.tsx -t AT_965_8_2`；預期突變：null 時顯示預設上限、停用列仍顯示「停用」，皆紅
  - 驗收字樣：[AT_OK_965_8_2]
- **AT-965-8-3**（vitest｜`WatchSourcesSection.test.tsx`｜Integration｜AC-965-8、W-R8；AC-R2P-24-8）新增流程與自動同步。
  - Given `ADMIN_UI`；fetch 替身可設各端點回應與請求記錄
  - When 填合法表單送出（POST 201）；填不合法表單送出；送出後 Bridge 回 422 `host_not_allowed`；送出後 POST 201 但隨後 sync 回 201／200／403／503／422／502／504
  - Then 不合法表單不送出且逐欄顯示錯誤（`aria-invalid`）；POST 成功後恰一次 `POST …/si/research-registry/sync`（本文 `{}`）、且在 POST 成功**之後**才送；POST 失敗（含 `host_not_allowed`，顯示「這個網域還沒開放，請先在上方網域清單新增」）不送 sync；sync 結果依 AT-965-8-6 的文案表顯示；成功後清單與狀態皆 refetch
  - 判定：`npx vitest run components/domain/research/WatchSourcesSection.test.tsx -t AT_965_8_3`；預期突變：POST 失敗仍送 sync、sync 送兩次，皆紅
  - 驗收字樣：[AT_OK_965_8_3]
- **AT-965-8-4**（vitest｜`WatchSourcesSection.test.tsx`｜Integration｜AC-965-8、W-R8；AC-R2P-24-8）停用與重新啟用。
  - Given 一列啟用、一列停用（`hostAllowed` 真）、一列停用（`hostAllowed` 假）
  - When 按「停用」「重新啟用」「重新啟用（網域未開放）」
  - Then 停用呼叫 `PATCH …/watch-sources/<slug>` 本文恰 `{enabled:false}`、重新啟用恰 `{enabled:true}`（`disabled_by` 由 backend 取 JWT subject，前端不送）；`hostAllowed` 假的停用列其「重新啟用」鈕停用且 `title` 說明原因（不送請求）；成功各自動 sync 一次；PATCH 失敗（404、422）顯示原因且不 sync
  - 判定：`npx vitest run components/domain/research/WatchSourcesSection.test.tsx -t AT_965_8_4`；預期突變：本文多帶 `disabledBy`、`hostAllowed` 假時仍可點，皆紅
  - 驗收字樣：[AT_OK_965_8_4]
- **AT-965-8-5**（vitest｜`WatchSourcesSection.test.tsx`、`researchRegistry.test.ts`｜Integration｜AC-965-8、W-R8、NFR-RR-3、NFR-RR-4；AC-R2P-24-8）同步狀態列文案。
  - Given 狀態夾具 `STATUS(state)`：`synced`、`unsynced`、`pending`（帶 `pendingTime`）、`unknown`（四種 `unknownCause`）
  - When 渲染狀態列（純函式 `registrySyncText(status)` 與元件共用）
  - Then `synced`＝「已同步到自我進化」；`unsynced`＝「有變更尚未同步」（從未同步 `ingestedSha256` 為 null 時加「尚未同步過」）；`pending`＝「已送出，待自我進化入帳（主機巡邏會自動處理）」並列送出時間；`unknown`＝「量不到同步狀態」加原因中文（`si_unavailable`＝自我進化目前讀不到；`scan_cap_exceeded`＝帳本太大掃不完；`bridge_unreachable`／`bridge_timeout`＝引擎橋接服務連不上或逾時）；`pending` 與 `unknown` 時**不出現**「已同步」字樣；文字為純文字、有 `role="status"`
  - 判定：`npx vitest run components/domain/research/WatchSourcesSection.test.tsx -t AT_965_8_5`；預期突變：`pending` 顯示「已同步」、`unknown` 顯示成已同步，皆紅
  - 驗收字樣：[AT_OK_965_8_5]
- **AT-965-8-6**（vitest｜`WatchSourcesSection.test.tsx`｜Integration｜AC-965-8、W-R8；AC-R2P-24-8）同步錯誤文案與重試。
  - Given sync 回應表：403 `si_write_forbidden`、503 `si_write_disabled`（兩種 cause）、503 `si_unavailable`、422 `registry_too_large`（兩種 `what`）、502、504（`outcomeUnknown` 真與假）、200 `unchanged`（`synced`／`pending`）、201 `written`
  - When 觸發 sync（自動或手動）
  - Then 文案依序：「此帳號不在自我進化寫入名單，未同步」、「自我進化的寫入功能尚未啟用（缺簽章金鑰或寫入權杖），未同步」、「自我進化暫時讀不到，稍後再試」、「追蹤來源總量超過可同步上限，請停用部分來源後再同步」、「連不上引擎橋接服務，未同步」、`outcomeUnknown` 真時「送出結果不明，稽核檔可能已落地，請先看狀態再決定是否重試」；`unchanged`＝「已是最新，未重送」；`written`＝「已送出，待入帳」（不含「已同步」）；除 403 與 `registry_too_large` 外皆有「重試」鈕；403 不顯示重試（重試無用）但保留手動鈕；文案取自 `researchRegistry.ts` 的單一表（`REGISTRY_SYNC_MESSAGES`），元件不內嵌第二份
  - 判定：`npx vitest run components/domain/research/WatchSourcesSection.test.tsx -t AT_965_8_6`；預期突變：403 也顯示重試、`written` 文案含「已同步」，皆紅
  - 驗收字樣：[AT_OK_965_8_6]
- **AT-965-8-7**（vitest｜`WatchSourcesSection.test.tsx`｜Integration｜AC-965-8、W-R8；AC-R2P-24-8）手動同步鈕與併發去重。
  - Given `ADMIN_UI`；sync 請求以閘門延遲回應
  - When 連點「同步到自我進化」三次；在 sync 進行中再新增一筆成功；sync 回應後再檢視
  - Then 進行中鈕 `disabled` 且 `aria-busy`、三次連點只送出一個請求；進行中新增成功後「恰再排一次」sync（尾隨去重，不平行送兩個）；`synced` 狀態下鈕仍可按（得 `unchanged` 文案）；成功後狀態查詢失效重取；OPERATOR 與 VIEWER 無此鈕（入口不渲染）
  - 判定：`npx vitest run components/domain/research/WatchSourcesSection.test.tsx -t AT_965_8_7`；預期突變：連點送多個、進行中新增不補排，皆紅
  - 驗收字樣：[AT_OK_965_8_7]
- **AT-965-8-8**（vitest｜`AllowlistDialog.test.tsx`｜Integration｜AC-965-8、NFR-RR-5；AC-R2P-24-8）角色、共用說明與既有 AT-960-19-8 不退步。
  - Given 既有 `AllowlistDialog.test.tsx` 夾具（補新端點的 fetch 替身：空清單與 `unsynced` 狀態；§4.1）；三種角色
  - When 跑既有 `AT_960_19_8*` 全部案例；另檢視網域區
  - Then 既有案例全綠（斷言語意不變）；僅 ADMIN 看得到入口（OPERATOR、VIEWER 不渲染，也不發任何 `watch-sources` 或 `research-registry` 請求）；網域清單區有說明句「研發工作流與自我進化共用這份網域清單」；追蹤來源區位於網域區之後且有獨立標題與 `aria-labelledby`
  - 判定：`npx vitest run components/domain/research/AllowlistDialog.test.tsx`；預期突變：非 ADMIN 仍發請求，皆紅
  - 驗收字樣：[AT_OK_965_8_8]
- **AT-965-8-E-1**（vitest｜`researchRegistry.static.test.ts`｜Unit｜AC-965-8、NFR-RR-6；AC-R2P-24-8）靜態掃描。
  - Given `components/domain/research/WatchSourcesSection.tsx` 與 `lib/domain/researchRegistry.ts` 原始碼
  - When 掃描
  - Then 不含 `dangerouslySetInnerHTML`；不含 `CONSOLE_SI_DECIDERS`、`deciders` 名單常數或任何帳號名字面；不含 `research_fetch_max` 的數值預設；API 回傳字串（`extract`、`url`、`message`）只以文字節點渲染；範圍非空（兩檔皆存在）並有負控（對含 `dangerouslySetInnerHTML` 的樣本回報）
  - 判定：`npx vitest run lib/domain/researchRegistry.static.test.ts -t AT_965_8_E_1`；預期突變：元件內嵌名單，皆紅
  - 驗收字樣：[AT_OK_965_8_E_1]
- **AT-965-8-E-2**（vitest｜`WatchSourcesSection.test.tsx`｜Integration｜AC-965-8、W-R10；AC-R2P-24-8）鍵盤、焦點與 aria。
  - Given `ADMIN_UI` 開對話框
  - When 以 Tab 走過追蹤來源區；觸發驗證錯誤；Esc 關閉對話框
  - Then 每個互動控件有可存取名稱；錯誤欄 `aria-invalid` 與關聯的錯誤文字；錯誤摘要 `role="alert"`；Tab 序＝清單鈕→新增表單欄位依視覺序→送出；Esc 關閉後焦點歸還到「研究來源設定」入口（同 AT-960-19-8 的行為）
  - 判定：`npx vitest run components/domain/research/WatchSourcesSection.test.tsx -t AT_965_8_E_2`；預期突變：新增表單欄位缺 label，皆紅
  - 驗收字樣：[AT_OK_965_8_E_2]
- **AT-965-9-1**（vitest｜`SiView.test.tsx`｜Integration｜AC-965-9、W-R9；AC-R2P-24-9）自我進化頁的一行說明。
  - Given `renderSi` 依序以 `ADMIN_UI`、`OPERATOR_UI`、`VIEWER_UI`
  - When 檢視頁面
  - Then 皆顯示「研究來源在『研發工作流 → 研究來源設定』統一管理」（逐字）；ADMIN 該句內有連結（`href="/research"`、可存取名稱含「研發工作流」）；OPERATOR 與 VIEWER 為純文字、無連結；說明列位於 `SiStatusBanner` 之後
  - 判定：`npx vitest run components/domain/si/SiView.test.tsx -t AT_965_9_1`；預期突變：非 ADMIN 也有連結，皆紅
  - 驗收字樣：[AT_OK_965_9_1]
- **AT-965-9-2**（vitest｜`lib/domain/si.test.ts`、`SiWritesPanel.test.tsx`｜Integration｜AC-965-9、W-R9；AC-R2P-24-9）對帳面板新 kind。
  - Given 對帳讀面回 `kind=src-registry` 的 `items` 與 `orphans`
  - When 渲染對帳面板；呼叫 `SI_WRITE_KIND_LABELS`、`ingestCommands`
  - Then `SiWriteKind` 為六值；`src-registry` 標籤為「研究來源同步」；`ingestCommands('src-registry', null, ref)`（簽章沿既有 `ingestCommands(kind, subject, auditRef)`）的 `powershell` 與 `posix` 皆為 `python tools/selfimproving.py registry-ingest --carrier console --audit-ref <ref>`（入帳動詞＝`registry-ingest`，D-EQA-16；與根層 `patrol._ingest_argv` 的 `["registry-ingest","--carrier","console","--audit-ref",ref,…]` 同動詞同旗標，根層 AT-645-4-1；其餘五種 kind 的既有指令逐字不變）；未知 kind 的既有降級行為不變
  - 判定：`npx vitest run lib/domain/si.test.ts -t AT_965_9_2`；預期突變：標籤缺、仍只認五值、動詞寫成 `registry-sync` 或漏 `--carrier console`，皆紅
  - 驗收字樣：[AT_OK_965_9_2]
- **AT-965-9-3**（vitest｜`lib/help/content.test.ts`、`lib/help/pageFacts.test.ts`｜Unit｜AC-965-9、W-R9；AC-R2P-24-9）每頁說明與既有說明鎖。
  - Given `lib/help/research-workspace.ts`、`lib/help/self-improving.ts`
  - When 跑既有說明鎖（出處鎖、名詞表、`sourceFiles`、`pageFacts`）
  - Then `research-workspace.ts` 的名詞表新增「追蹤來源」「同步到自我進化」兩列（`source` 欄指向 `WatchSourcesSection.tsx` 與 `researchRegistry.ts`），`sourceFiles` 含 `components/domain/research/WatchSourcesSection.tsx`；`self-improving.ts` 有統一管理說明一句；既有鎖全綠；新增名詞與畫面字樣逐字一致（出處鎖）
  - 判定：`npx vitest run lib/help`；預期突變：說明字樣與畫面不符，皆紅
  - 驗收字樣：[AT_OK_965_9_3]
- **AT-965-9-4**（vitest｜`lib/api/si.endpoints.test.ts`、`lib/api/research.endpoints.test.ts`｜Unit｜AC-965-9、W-R8；AC-R2P-24-9）`schema.d.ts` 與端點函式。
  - Given 重產後的 `lib/api/schema.d.ts` 與 `endpoints.ts` 新函式
  - When 呼叫 `listWatchSources`、`addWatchSource`、`patchWatchSource`、`getRegistrySyncStatus`、`postRegistrySync`
  - Then 路徑與方法正確（`/api/v1/research/watch-sources`、`/{slug}`、`/api/v1/si/research-registry`、`…/sync`）、本文為 camelCase、`ApiError` 帶 `reason` 與 `details`；`schema.d.ts` 含三個新 operationId 與兩個 SI 操作；`RESEARCH_REGISTRY_REASONS` 恰三值且與契約 §0.2 第 7a′ 列、backend `REGISTRY_` 常數三處相等（靜態比對）
  - 判定：`npx vitest run lib/api/si.endpoints.test.ts lib/api/research.endpoints.test.ts -t AT_965_9_4`；預期突變：reason 常數漏一個，皆紅
  - 驗收字樣：[AT_OK_965_9_4]
- **AT-965-9-5**（vitest｜`SiStatusBanner.test.tsx`｜Integration｜AC-965-9、W-R9、D-EQA-5；AC-R2P-24-9）橫幅三鍵具名呈現（仿 `AT_964_1_3`）。
  - Given `renderSi` 以 `ADMIN_UI`；`statusItem()` 夾具含 SI `status.items[0]` 的 `researchFetchMax`（整數）、`researchRegistry`（`{seq, auditRef, registrySha256, watchEnabled}`，D-RR-15；鍵一律 camelCase，勘誤 E-7）與 `backtest`（根層 PRD v0.15 AC-SI-46-8 欄位：`casesVersion`、`casesSha256`〔全值 `sha256:`＋64 位十六進位，夾具照此給；橫幅才取前 12 碼顯示〕、`n`、`hit1`、`hit3`、`hit5`、`precPm`、`recPm`、`contaminated`、`hit5Trend`〔本 AT 不顯示〕，無事件＝null）；依序六組：三鍵齊全；`researchRegistry` 為 null；`backtest` 為 null；`researchFetchMax` 缺鍵；三鍵全 null／缺；`backtest` 欄位型別不符（例 `hit3` 為字串）
  - When 檢視橫幅
  - Then `SI_STATUS_KNOWN_KEYS` 含 `researchFetchMax`、`researchRegistry`、`backtest`（三鍵**不出現**在「其他欄位」）；齊全時顯示兩個具名欄位：「研究來源：啟用 N／上限 M；最近同步 seq S（sha 前 12 碼）」（`N`＝`researchRegistry.watchEnabled`、`M`＝`researchFetchMax`、`S`＝`seq`、sha 取 `registrySha256` 去 `sha256:` 前綴後前 12 碼）與「反事實回測：案例集 v`casesVersion`（sha 前 12 碼）；hit@3＝`hit3`／`n` 案、污染 `contaminated`」；值為 null 的鍵顯示「尚無」（不顯示成 0 或空白）；缺鍵或型別不符一律顯示「量不到」（沿 NFR-SC-2，不顯示成「尚無」或 0）；全部為純文字節點；與研究來源設定的同步狀態文案互不混用（本欄位只呈現 SI 鏡像的事實，不判斷 synced）
  - 判定：`npx vitest run components/domain/si/SiStatusBanner.test.tsx -t AT_965_9_5`；預期突變：未把三鍵加入 `SI_STATUS_KNOWN_KEYS`（落入「其他欄位」）、null 顯示成 0、缺鍵顯示成「尚無」，皆紅
  - 驗收字樣：[AT_OK_965_9_5]

**E. E2E（Playwright）**

- **AT-965-10-1**（Playwright｜`research-docker.stack.spec.ts`｜E2E｜AC-965-10、W-R10、NFR-RR-9；AC-R2P-24-10）Docker 全棧：種子、新增、同步、稽核檔。
  - Given `E2E_STACK=1`、`E2E_ADMIN_*`（該帳號在全棧的 `CONSOLE_SI_DECIDERS`）、Docker 全棧（含 `BRIDGE_SI_AUDIT_DIR` 掛容器卷，非主機真 SI 家目錄；`BRIDGE_SI_WRITE_TOKEN`、`CONSOLE_SI_AUDIT_KEY` 已設）；mock claude；測試先以 `docker exec` 列出稽核目錄現況（N 個檔）
  - When ADMIN 登入→`/research`→開「研究來源設定」→檢視追蹤來源區→新增 `e2e-<時戳>`（host `www.anthropic.com`，kind `blog`）→等待狀態列→開「同步到自我進化」狀態變化→讀稽核目錄→收尾以 UI 停用該列（並自動同步）
  - Then 看到種子 17 列（啟用 10）；新增後狀態列先顯示「有變更尚未同步」、自動 sync 後顯示「待入帳」（全棧沒有主機巡邏，故不會自動變「已同步」）；稽核目錄恰多一個 `<audit_ref>.json`（N＋1；收尾停用後再多一個）、外層 `kind` 為 `src-registry`、外層七鍵、`subject` 為 null；以 Python 一行重算 `sha256(body.registry_text)` 等於 `body.registry_sha256`，且 `registry_text` 含該 `e2e-` slug；DB `console.si_console_writes` 多對應列且 `digest` 等於 `registry_sha256`；該容器卷路徑不在主機 `~/.autosdd` 之下（斷言掛載來源）；收尾後該列在清單中為停用
  - 判定：`npx playwright test tests/e2e/research-docker.stack.spec.ts -g AT_965_10_1`（cwd＝`AgentConsole/frontend`；全棧需先 `docker compose --profile db --profile app --profile full up -d --build`）；預期突變：同步未送出、稽核檔 kind 錯、digest 不等，皆紅
  - 驗收字樣：[AT_OK_965_10_1]
- **AT-965-10-3**（pytest｜`engine-bridge/tests/test_si_deploy_config.py`｜結構鎖｜AC-965-10、NFR-RR-9；勘誤 E-11）Bridge 映像預建並 chown 稽核目錄。
  - Given `docker-compose.yml` 的 engine-bridge 服務設有 `BRIDGE_SI_AUDIT_DIR`（現值 `/si-audit`）；`AgentConsole/engine-bridge/Dockerfile` 文字
  - When 純函式 `audit_dir_image_problems(dockerfile_text, compose)` 檢視
  - Then 該目錄同時出現在 `USER bridge` 之前的 `mkdir -p` 與 `chown bridge:bridge` 目錄清單（具名卷首次掛載繼承映像內目錄擁有者，否則卷為 root 擁有、Bridge uid 10001 寫入 EACCES ⇒ 同步 503）；真檔回空清單；負控逐一回對應訊息：缺 mkdir、缺 chown、chown 在 `USER bridge` 之後、compose 改路徑而 Dockerfile 未跟上、compose 缺該變數
  - 判定：`python -m pytest tests/test_si_deploy_config.py -q -k AT_965_10_3`（cwd＝`AgentConsole/engine-bridge`）；預期突變：Dockerfile 的 chown 清單拿掉 `/si-audit`，紅
  - 驗收字樣：[AT_OK_965_10_3]
- **AT-965-10-2**（Playwright｜`a11y.mock.spec.ts`｜E2E｜AC-965-10、W-R10；AC-R2P-24-10）三寬度 axe 零違規與無橫向溢出。
  - Given `E2E_MODE=standalone` 的 mock API（路由含 `watch-sources`、`si/research-registry` 與既有 allowlist；種子 17 列夾具與四種狀態）
  - When 以 `RESEARCH_WIDTHS`（1440、1000、600）開研究來源設定對話框（含追蹤來源區、新增表單展開、錯誤狀態、`unknown` 狀態）
  - Then 各寬度 `expectNoA11yViolations`（serious／critical 零）；對話框內 `scrollWidth ≤ clientWidth`、頁面無橫向捲動；表格在窄寬可橫向捲動容器內且不撐破對話框；網域表（上半）同樣在可橫捲容器內、表寬不被擠壓〔勘誤 E-13 補〕；焦點可見；狀態徽章對比度≥4.5
  - 判定：`npx playwright test tests/e2e/a11y.mock.spec.ts -g AT_965_10_2`；預期突變：追蹤來源表在 600 寬撐出橫向溢出、按鈕無可存取名稱，皆紅
  - 驗收字樣：[AT_OK_965_10_2]
- **AT-965-10-4**（Playwright｜`self-improving-schedule.mock.spec.ts`｜E2E｜AC-965-10、AC-965-9；勘誤 E-14、DEF-AC-039）ADMIN 自我進化頁的研究來源說明連結無對比違規。
  - Given `E2E_MODE=standalone` 的 mock API；ADMIN 角色（說明句內的「研發工作流 → 研究來源設定」連結只在 ADMIN 渲染）
  - When 開 `/self-improving`（預設分頁），先確認該連結可見，再對整頁跑 axe
  - Then `expectNoA11yViolations`（serious／critical 零）；主控台無錯誤
  - 判定：`npx playwright test tests/e2e/self-improving-schedule.mock.spec.ts -g AT_965_10_4`；預期突變：連結文字色改回主色（頁面底色上對比 4.21，低於 4.5），紅
  - 驗收字樣：[AT_OK_965_10_4]
- **AT-965-10-E-1**（Playwright｜`research-registry.mock.spec.ts`〔新〕｜E2E｜AC-965-10、W-R8；AC-R2P-24-10）非名單 ADMIN 的同步被拒（mock）。
  - Given `E2E_MODE=standalone`；mock 路由對 `POST …/si/research-registry/sync` 回 403 `si_write_forbidden`；ADMIN 角色
  - When 新增一筆追蹤來源（mock POST 201）
  - Then 新增成功後出現「此帳號不在自我進化寫入名單，未同步」且無重試鈕；狀態列仍為「有變更尚未同步」；清單含新列；沒有額外的 sync 請求（恰一次）
  - 判定：`npx playwright test tests/e2e/research-registry.mock.spec.ts -g AT_965_10_E_1`；預期突變：403 後自動重試、清單不更新，皆紅
  - 驗收字樣：[AT_OK_965_10_E_1]

---

## 3. AT 完整清單

依「測試住在哪一側」分類（AT 6-7 跨 backend 與 Bridge，兩側各有一個測試函式、計入兩側各一次但只算一個 AT）：

- **3.1 backend（JUnit）**：AT-965-1-1～1-7、1-E-1（8）；AT-965-2-1～2-3（3）；AT-965-5-1～5-6、5-E-1（7）；AT-965-6-1～6-5、6-7（Java 端）、6-8、6-9、6-E-1（9）；AT-965-7-1～7-5（5）；合計 32 個 AT（含 6-7）。
- **3.2 Bridge（pytest）**：AT-965-3-1～3-9、3-E-1（10）；AT-965-4-1～4-9、4-E-1、4-E-2（11）；AT-965-6-6（1）；AT-965-10-3（1，結構鎖；勘誤 E-11）；AT-965-6-7（Python 端，與 3.1 同一個 AT）；合計 23 個 AT（不含 6-7）。
- **3.3 frontend（vitest）**：AT-965-8-1～8-8、8-E-1、8-E-2（10）；AT-965-9-1～9-5（5）；合計 15 個 AT。
- **3.4 Playwright**：AT-965-10-1、10-2、10-4（勘誤 E-14）、10-E-1；合計 4 個 AT。

**計數核對**：32＋23＋15＋4＝74；亦等於各 AC 分項加總：AC-965-1（8）＋AC-965-2（3）＋AC-965-3（10）＋AC-965-4（11）＋AC-965-5（7）＋AC-965-6（10）＋AC-965-7（5）＋AC-965-8（10）＋AC-965-9（5）＋AC-965-10（5）＝74。編號含 `E` 者 9 個：1-E-1、3-E-1、4-E-1、4-E-2、5-E-1、6-E-1、8-E-1、8-E-2、10-E-1。（QA 一審前為 68，D-EQA-3、5、7 新增 4-E-1、4-E-2、9-5、6-9 共 4 個。）

---

## 4. 邊界與錯誤測試規格，與需同步的既有測試

| 類別 | 情境 | 預期 |
|------|------|------|
| 邊界 | slug 32／33 字元；url 500／501 字元；extract 200／201 字元；expand.max 1／3／0／4；`registry_text` 24576／24577 位元組；外層檔 65536／65537 位元組 | 前者通過、後者被拒（依各 AT） |
| 邊界 | host 含連字號、數字開頭、最長 253 字元；punycode host | 合規者通過；超長被擋 |
| 錯誤 | Bridge 無 DSN、無權杖、逾時、不可達 | 依 §0.2 與 AT-965-3-9、5-4、6-2 |
| 競態 | 兩個並行 sync 同 digest | **已知殘餘**：可能各落一列（同 P2b 重送閘的殘餘處置）；由對帳讀面顯示兩列待入帳，不另加唯一約束（A→B→A 合法重送會被誤擋）；不設 AT，記於 §7.1 |
| 競態 | 同步進行中追蹤來源又變更 | 下一次 sync 補上；AT-965-8-7 的尾隨去重保證不遺漏 |

### 4.1 需同步的既有測試（只改預期值；不弱化斷言；本表外既有函式因本鍵而紅者，開發 agent 以純文字回報、由主控裁決後補入本表）

| 既有測試（檔:行；撰寫時現查） | 現況 | 改為 | 原因 |
|---|---|---|---|
| `ResearchSchemaMigrationIT.java:504`（`AT_960_1_1*`）、`:1741`（`AT_961_1_1*`）、`:2328`（`AT_962_1_1*`） | Flyway 版本清單終於 `"23"` | 加 `"24", "25"` | 新遷移 V24、V25 |
| `ResearchSchemaMigrationIT.java:535`（`AT_960_1_1*`，`guardsByTable.keySet()` 全等於十八表） | 恰十八張 | 加第十九張 `research_watch_sources`（掛 `research_controlled_update_guard` 單一守衛；新表的表名常數 `V24_TABLES`） | 新表（沿 `research_` 前綴） |
| `ResearchSchemaMigrationIT.java:2242`（`AT_961_1_E_1*`）、`:2486`（`AT_962_1_6*`）：`hasSize(18)` 與 `expectedTables` | 十八張（P0 十三加 V19 五） | 十九張（加 V24 一）；「至少一列」「DELETE 一律被擋」迴圈自動涵蓋新表（種子保證至少一列） | 新表 |
| `BackupJobMigrationIT.java:173,196,215`、`IssuePriorityMigrationIT.java:131`、`SchemaMigrationIT.java:69`、`SiConsoleWritesMigrationIT.java:129`、`V5UpgradeMigrationIT.java:136` | Flyway 版本清單終於 `"23"` | 加 `"24", "25"` | 同上 |
| `OpenApiIT.java:295,300`（`AT_964_7_7*`）：路徑總數 116、操作總數 133 | 116／133 | 現值（撰寫時 116／133）加本鍵新增：路徑＋4（`/api/v1/research/watch-sources`、`…/{slug}`、`/api/v1/si/research-registry`、`…/sync`）、操作＋5（watch 三個、SI 兩個）→ 120／138（實作時以現查為準） | 新端點 |
| `OpenApiIT.java:303`（`AT_964_7_7*`）：`SiWriteKind` `containsExactly` 五值 | 五值 | 加 `"src-registry"`（六值，順序同枚舉宣告） | `SiWriteKind.SRC_REGISTRY` |
| `OpenApiIT.java:1197,1206,1225`（`AT_960_5_5*` 三案）：研究路徑 37、有 operationId 的研究操作 41、研究操作狀態碼表 42 | 37／41／42 | 39（加 2 條路徑）、44（加 3）、45（加 3）；`RESEARCH_OPERATION_IDS` 與 `RESEARCH_STATUS_CODES` 表加三個新操作 | `/api/v1/research/watch-sources*` 屬研究路徑（`isResearchPath`） |
| `ResearchReasonsTest`（`AT_960_5_6*`、`AT_961_15_4*`） | 三十七個 reason 四處全等 | **零改動**（新 reason 自成 `REGISTRY_` 家族，不以 `RESEARCH_` 為前綴；契約 §0.2 的新列僅增 `contains` 命中，不影響該鎖） | D-176(11) |
| `ResearchApiIT`／`RbacIT`（`AT_960_5_1*`、`AT_960_5_4*`） | 對 allowlist 的矩陣 | **零改動**（AT-965-5-5 以原斷言重跑佐證） | W-R0 |
| `AllowlistDialog.test.tsx`（`AT_960_19_8*` 全部案例）、`console-sort.mock.spec.ts:15`、`a11y.mock.spec.ts:241`、`research-build-front.mock.spec.ts:25`、`research-deliver.mock.spec.ts:60`（mock 路由） | 只 mock `/api/v1/research/allowlist` | 補 `/api/v1/research/watch-sources`（回 `{data: []}`）與 `/api/v1/si/research-registry`（回 `unsynced` 夾具）兩條路由；斷言語意不變 | 對話框新增追蹤來源區後會發新請求 |
| `lib/help/research-workspace.ts`、`self-improving.ts` 與 `content.test.ts`／`pageFacts.test.ts` 的釘選（名詞表列數、`sourceFiles` 清單、說明字樣） | 無新名詞 | 加兩個名詞列、`sourceFiles` 加 `WatchSourcesSection.tsx`、`pageFacts` 的對應事實 | 每頁說明同步（AT-965-9-3） |
| `lib/api/schema.d.ts`（入庫快照） | 無新操作 | 重產 | 新 operationId |
| Bridge `tests/test_research_router.py` `AT_960_8_9*`（`:817` 起） | 有效 FETCH 清單為「五個基底主機」 | 若該案以含種子的真 PG 建庫則加四個種子網域；若以替身 DB 則零改動（**撰寫時未逐行確認 `Env`／`RDB` 夾具是否跑遷移，開發 agent 先跑該案、以紅燈為準回報**） | 種子網域 |

**實作輪補註（勘誤 E-4）**：`WATCH_OPS` 另立為獨立集合，不併入 `OPS`／`METHOD_KINDS`（保留既有 20 方法鎖）。

**本鍵沒有找到因「種子加入 4 個 FETCH 網域」而必然失效的既有 AT**：撰寫時逐一讀過 `AT-960-5-4`（迷你 Bridge 回放，與資料庫種子無關）、`AT-960-19-8`（fetch 替身）、`AT-960-1-4`（自行 INSERT 的 host 為 `export.arxiv.org` 與 `reddit.com` 等，不與種子 host 衝突）、`ResearchSchemaMigrationIT:703-752`（逐列快照比對，不計總列數）；失效面來自「遷移版本清單」「`research_` 表數十八」「OpenAPI 計數」。唯一未確認的是上表最後一列（Bridge `AT_960_8_9*`）。

**R2P 既有 TCS 勘誤稿（本檔不改原檔，交主控走 `spec-refreeze`；原文逐字保留於勘誤表）**

| 號 | 檔／AT | 原文 | 改文 | 來源 |
|---|---|---|---|---|
| R-1 | `TCS-ResearchToPRD-P1-20261107.md` AT-961-1-E-1 標題與 Then | 「所有十八張 research_ 表（P0 十三張加 V19 五張）逐表 DELETE 一律被擋」 | 「所有十九張 research_ 表（P0 十三張、V19 五張、V24 一張〔`research_watch_sources`〕）逐表 DELETE 一律被擋，SQLSTATE 一律為類別 23」 | 鍵 `agentconsole-research-registry`；W-R1 |
| R-2 | `TCS-ResearchToPRD-P2-20261107.md` AT-962-1-6 標題與 Then | 「十八張 research_ 表逐表 DELETE 仍被擋、受控表清單與 append-only 清單不變」 | 「十九張 research_ 表……受控表清單加 `research_watch_sources`、append-only 清單不變」 | 同上 |
| R-3 | `TCS-ResearchToPRD-P0-20261102.md` AT-960-1-1 標題 | 「Flyway 歷史 1～18 全成功、13 張新表與序列／函式／守衛函式齊備且只在 console schema」 | 加註「（本 AT 的程式碼自 P1 起以最新版斷言版本清單與守衛表集合；V24 起加第十九張表 `research_watch_sources`，其守衛掛既有通用守衛函式）」 | 同上（澄清型） |
| R-4 | `TCS-ResearchToPRD-P0-20261102.md` AT-960-5-4 Then、AT-960-8-9 Then、AT-960-19-8 Given | 「GET 在預設部署回恰四組基底主機」「預設有效 FETCH 清單恰為五個基底主機」「allowlist GET 回四組基底主機與一個 ADMIN 條目」 | 各句的「基底主機」限定為 `source=ENV` 條目；加註「含 V24 種子的庫另有四個 `source=ADMIN`、FETCH 條目；本 AT 的夾具（迷你 Bridge／替身）不含種子，程式碼零改」 | D-173；PRD 勘誤第 32 列（澄清型） |
| R-5 | `TCS-ResearchToPRD-P0-20261102.md` AT-960-5-5（及 P1、P2 TCS 中同 AT 的計數敘述） | 「研究路徑 37 條：P0 的 24 條加 P1 的 6 條加 P2 的 7 條」「有 operationId 的研究操作 41」「42 個研究操作」 | 39、44、45，並註「加增量 `/api/v1/research/watch-sources*` 兩條路徑三個操作」 | 鍵 `agentconsole-research-registry`；§4.1 |
| R-6 | `TCS-SelfImprovingSchedule-20261109.md` AT-964-7-7 Then | 「路徑總數＝修改前現值 114 加 2」「操作總數＝修改前現值 131 加 2」「`SiWriteKind` 全等為五值」 | 以當時實值遞增（120／138）與六值（加 `src-registry`）；本檔只登記，**該 TCS 凍結於鍵 `agentconsole-si-schedule`，主控決定是補勘誤並 refreeze 該鍵，或僅改程式碼預期值並在本檔 §4.1 留痕（建議後者：該預期值本質是「現值」，P4 當時即以「修改前現值加 N」寫成累加式）** | §7.2 第 3 項 |

**需要 `spec-refreeze` 的鍵**：`agentconsole-research-to-prd-p0`、`agentconsole-research-to-prd-p1`、`agentconsole-research-to-prd-p2`（各自凍結了 `ResearchToPRD_PRD.md` 與 `API_Contract_ResearchToPRD.md`，本增量原地修訂兩檔；R-1～R-5 同時落在各自的 TCS：P0 TCS 屬 p0 鍵、P1 TCS 屬 p1 鍵、P2 TCS 屬 p2 鍵）。**不需要**重凍：`Architecture.md` 與 `API_Contract_SelfImproving_P2b／P2c.md` 未修改，故持有它們的其他八把鍵不受影響；`agentconsole-si-schedule` 僅在主控採 R-6 的「補勘誤」方案時才需重凍。

---

## 5. 測試資料規格

### 5.1 常數與資料

- `REGISTRY_TEXT_MAX_BYTES`＝24576（Bridge `app/research/registry.py` 唯一定義處）；`SI_WRITE_BODY_MAX_BYTES`＝65536（既有，`routers/si.py:62`）；外層檔上限以 `SI_WRITE_BODY_MAX_BYTES` 為準，console-api 以同值常數（`SiWriteProperties` 或 `SiBridgeLimits`）持有並由 AT-965-6-5 的 `limit` 斷言同源。
- 種子夾具 `seed_si_sources.json`：byte-identical 複本，來源 `docs/06_quality/SelfImproving_Protocol/research_sources.json`（commit `8b6950d2`，檔案 sha256 `6201d066799e7f13c18053f3474f6883fddd8091baf0ab24e3a4b1c0d348e26f`）；舊表依 D-RR-20 **凍結、不刪**（史料；根層不再讀它抓取，`check` 仍驗它與歷史事件雜湊），本夾具與舊表同為只讀對照物，AT 先驗夾具 sha（防夾具漂移）。
- **共享附錄（D-EQA-3）**：以下四份的唯一本文住根層 `docs/03_testing/contracts/TCS-SelfImproving-P6-20261110.md` 附錄 A～D（圍欄內文字的位元組與 sha256 見該檔附錄 E）；**本檔不複製全文**，只以「路徑＋位元組數＋sha256」引用；Console 端測試取該檔圍欄內文字為夾具（主控把圍欄內文字原樣抽成檔複製到 `AgentConsole/engine-bridge/tests/fixtures/research_registry/appendix-{a,b,d}.txt|json`，Bridge 測試先重算複本 sha256 等於下表值才跑，不符＝紅）：

  | 附錄 | 內容 | 位元組 | sha256 | Console 端消費者 |
  |---|---|---|---|---|
  | A | 公網位址表（`位址<TAB>T｜F`） | 441 | `3101fd6aaebaf80e51d5161b3dee4ea87e8c9b15d2ac1a09f7c58ce55f230afd` | AT-965-4-E-1（`is_public_ip` 逐列） |
  | B | golden 鏡像 `registry_text`（`registry_sha256`＝`sha256:147fccd6…f0e8`） | 2039 | `147fccd6a1b9efb61423579e26fbbc7437366a937806e239c69f334732aff0e8` | AT-965-4-E-2（`GET /research/registry` 逐位元組）、AT-965-6-1、AT-965-6-7 |
  | C | 稽核檔位元組表（G-S1 產生規則） | 1681 | `91f137380530a5959138597add7b145ab7760611a7cca0ac1d7861062d321d87` | AT-965-6-7 |
  | D | 追蹤來源 URL parity 表（`URL<TAB>SI<TAB>CON`） | 1797 | `25fd334dc97b8d135393849851962abfb54a621f11f9f0b1ba80eb27f4de1e89` | AT-965-1-7（DB CHECK）、AT-965-3-3（Bridge）、AT-965-8-1（前端） |

- 黃金檔：**G-R1**（契約 §5A.3 逐字，Console 自有的最小空登記，205 位元組，`registry_sha256`＝`sha256:73123a2bf0275448928199a72895297c77d6af8773ffa14b7cf453d19dc393a3`）；**附錄 B golden** 取代原 附錄 B golden（Console 不再自持含三列追蹤來源的 golden）；**G-S1**＝根層實作輪產出的 `tools/tests/fixtures/selfimproving/G-S1.audit.json`，Console 副本路徑固定 `AgentConsole/backend/src/test/resources/si/G-S1.audit.json`（主控原樣複製；根層 AT-645-1-8 只驗根層檔對附錄 C、不讀本路徑，副本一致性由 AT-965-6-7 負責——QA2-01），Console **不自產 G-S1**（D-EQA-2）。
- 原「共用期望表 `watch_url_cases.json`」由附錄 D 取代（Bridge 與前端各自消費附錄 D 的複本）。
- 帳號：`admin`（ADMIN、在 `console.si.deciders`）、`admin2`（ADMIN、不在名單）、`operator`、`viewer`；金鑰 `K0` 與權杖為測試哨兵值（非真機密）。

### 5.5 backend 測試設施（沿 P2b TCS §5.4、P4 TCS §5.5；只增不改）

`AbstractApiIT` 迷你 Bridge 加路由：`GET／POST／PATCH /research/watch-sources`（記錄請求）、`GET /research/registry`（`MINI.registry`）、`POST /si/registry:sync`（`MINI.si.writes`）；`MINI.events` 設定 `GET /si/events` 的分頁內容（含 `research.registry` 事件列）；`SiWriteSeam` 沿用；新增 `ResearchWatchSourceSchemaIT`（沿 `ResearchSchemaMigrationIT` 的 Testcontainers 體例）。

### 5.6 frontend 與 Playwright 測試設施

`WS(over)`、`STATUS(state, over)` 夾具與 fetch 替身路由加於 `tests/helpers/`（新檔 `researchRegistry.tsx`，沿 `tests/helpers/si.tsx` 體例）；mock spec 路由補兩條（§4.1）；真棧 spec 沿 `research-docker.stack.spec.ts` 既有登入與 `docker exec` 輔助。

### 5.7 hermetic 環境與允許變更的檔案集合

- **允許變更**（三包持有面）：D1～D7 所列路徑，加 §4.1 所列既有測試檔的預期值與 mock 路由；本鍵**不得**動：根層 `tools/`、`.claude/`、`.github/`、根 `CLAUDE.md`、`AgentConsole/docs/02_architecture/Architecture.md`（最小文件集）、既有 Flyway 檔（V1～V23）、既有 TCS 與契約原文（勘誤由主控落）、`app/research/fetch/` 抓取層。
- AT 不連外網、不寫真 SI 家目錄、不讀真帳本；Testcontainers PG 與迷你 Bridge 為唯一外部依賴；Docker 全棧 E2E 的稽核目錄為容器卷（AT-965-10-1 斷言）。

---

## 6. RTM 連結確認

### 6.1 追溯

| 需求 | AC（PRD）｜AC（本檔） | AT |
|------|----------------------|-----|
| FR-R2P-24 描述：兩層登記、種子 | AC-R2P-24-1｜AC-965-1 | AT-965-1-1～1-7、1-E-1 |
| FR-R2P-24：kind 放寬 | AC-R2P-24-2｜AC-965-2 | AT-965-2-1～2-3 |
| FR-R2P-24：Bridge CRUD、單一閘 | AC-R2P-24-3｜AC-965-3 | AT-965-3-1～3-9、3-E-1 |
| FR-R2P-24：登記快照（D-172） | AC-R2P-24-4｜AC-965-4 | AT-965-4-1～4-9、4-E-1、4-E-2 |
| FR-R2P-24：角色與審計、R2P 零退步 | AC-R2P-24-5｜AC-965-5 | AT-965-5-1～5-6、5-E-1 |
| FR-R2P-24：同步端點 | AC-R2P-24-6｜AC-965-6 | AT-965-6-1～6-8、6-E-1 |
| FR-R2P-24：狀態判定 | AC-R2P-24-7｜AC-965-7 | AT-965-7-1～7-5 |
| FR-R2P-24：前端追蹤來源區與同步 | AC-R2P-24-8｜AC-965-8 | AT-965-8-1～8-8、8-E-1、8-E-2 |
| FR-R2P-24：自我進化頁、說明 | AC-R2P-24-9｜AC-965-9 | AT-965-9-1～9-5 |
| FR-R2P-24：E2E 與無障礙 | AC-R2P-24-10｜AC-965-10 | AT-965-10-1～10-4、10-E-1（10-3 見勘誤 E-11、10-4 見勘誤 E-14） |
| NFR-RR-1～9 | — | 見 NFR 表「驗證 AT」欄 |

### 6.2 V 系列：實查檢核（QA、主控、掌舵者；**不是 AT**，結果寫進 SCG-4 報告與 RTM 備註；未驗者如實標「未驗」，構造情境不得充當）

- **V1（主控，真機）**：Windows 本機真全棧（含主機 `~/.autosdd`）：ADMIN 開研究來源設定，目視 17 列種子、10 啟用；新增一筆→「待入帳」；等根層巡邏入帳後狀態轉「已同步」。**此項需根層實作完成**；結果寫入 RTM 備註與帳本，測試列收尾停用。
- **V2（主控）**：入帳後主機 SI 鏡像檔 `docs/06_quality/SelfImproving_Protocol/research_registry.json` 的位元組＝Console 當下 `GET /research/registry` 的 `registry_text`（逐位元組 `fc`／`sha256` 比對）。
- **V3（QA）**：把 `anthropic-engineering` 對照 `anthropic-research` 的種子語意：以 `sitemap.xml` 實抓（根層 SI `si research --fetch`）取得 3 篇文章純文字——屬根層驗收，本檔只記接縫。
- **V4（QA）**：既有研究 AT 全套（`ResearchApiIT`、`RbacIT`、`ResearchReasonsTest`、`ResearchArchTest`、Bridge `test_research_*`、前端 research 元件測試）逐檔重跑，列出預期值改動恰等於 §4.1。
- **V5（主控）**：全套 `gradlew clean build`、Bridge `pytest` 與 `ruff check`（兩視角）、前端 `lint`／`tsc --noEmit`／`build`／`vitest`。
- **V6（QA）**：Linux（CI）與 Windows 各跑一次本鍵新增 AT；macOS 未驗（如實標）。
- **V7（掌舵者，目視）**：研究來源設定對話框的版面與文案（國高中白話）；窄寬可用。〔訂正（勘誤 E-12）：改由代理截圖代驗——長駐棧以 ADMIN 唯讀開啟對話框（不新增、不停用、不同步），於 1440／1000／375 三種寬度截圖並跑 axe（無 serious／critical）、確認無水平溢出且控制項在 375 寬可用、逐段對照文案是否國高中白話並與規格用語一致；結果與截圖路徑寫 RTM 的 V7 列〕
- **V8（QA）**：`SI_WRITE_BODY_MAX_BYTES` 與 `REGISTRY_TEXT_MAX_BYTES` 的餘裕：以種子加十個典型新增逼近上限，確認 422 `registry_too_large` 出現在預期處並有清楚文案。

---

## 7. 本檔採用的預設裁決與開放問題（掌舵者可推翻；推翻走 T1 或本檔修訂，凍結前由主控回報掌舵者）

### 7.1 裁決與預設

1. 表名 `research_watch_sources`、主鍵 `slug`、無代理 UUID（PATCH 以 slug 定位；`audit_log.entity_id` 取 slug）。
2. 通用守衛以 `CREATE OR REPLACE` 擴充既有函式（不另立守衛函式）；以 AT-965-1-6 對拍九條既有條目。
3. `expand` 用型別化三欄；`kind` 六值（SI 四值加 `sitemap`、`search`）。
4. 重新啟用清空 `disabled_by`／`disabled_at`（digest 往返一致）。
5. 追蹤來源端點在 `/api/v1/research/watch-sources`；同步與狀態在 `/api/v1/si/research-registry*`（沿既有 `POST /api/v1/si/**` ADMIN 規則）。
6. 鏡像讀不到：同步 fail-closed（503 `si_unavailable`）、狀態降級 `unknown`。
7. 冪等只比最新一筆；不提供 force；並行重複為已知殘餘。
8. 新 reason 三個自成 `REGISTRY_` 家族，不進既有三十七個研究 reason。
9. Console 不持有 `research_fetch_max`；只轉鏡像值。
10. **不修改 Architecture.md**（最小文件集）：Architecture §7 資料所有權、§10 Bridge 契約、§11.1 研究端點簡表因此缺新表與新端點的簡表列，記為已知債；其「`console` 表清單」類的機械鎖（若有）以本鍵實作輪現查為準，若有紅燈則回報主控裁決是否補 Architecture（連動多鍵 refreeze）。
11. 稽核 body 鍵序 `…,time,registry_text,registry_sha256`（決策書列舉序）；`registry_text` 與 `registry_sha256` 的先後以根層 TCS 位元組表為準，兩側黃金檔交叉核對時如不同則以根層為準並同步改契約 §5A.4。
12. `REGISTRY_TEXT_MAX_BYTES`＝24576、外層檔 65536 雙層檢查。

### 7.2 SD 對上位文件與現況的發現（供主控處理；本檔未改任何凍結檔）

1. **種子對 R2P 既有 AT 的實際影響很小**（見 §4.1 末段）；真正的連動面是 Flyway 版本清單（八支 IT）、`research_` 表數（三案 `hasSize(18)`）與 OpenAPI 計數（`OpenApiIT` 三處），皆為預期值改動。
2. **`ResearchReasonsTest` 會逼 Architecture §11.1 逐項列出 `RESEARCH_` 前綴 reason**：這是本鍵把新 reason 獨立成 `REGISTRY_` 家族的原因；若主控偏好把三個 reason 併入研究 reason 集合，需同改 `ErrorReasons`、前端 `RESEARCH_REASONS`、契約 §0.2、Architecture §11.1 並重凍多把鍵。
3. **`OpenApiIT` 的 `AT_964_7_7` 預期值屬於 `TCS-SelfImprovingSchedule`（鍵 `agentconsole-si-schedule`）**：本鍵新增端點與 `SiWriteKind` 值會使它的計數與五值斷言必須改；因斷言寫成「修改前現值加 N」，建議只改程式碼預期值並在本檔留痕，不為此重凍 `si-schedule` 鍵（見 R-6）。
4. **入帳指令（已定，D-EQA-16）**：入帳動詞＝`registry-ingest`；`ingestCommands('src-registry', null, ref)` 回 `python tools/selfimproving.py registry-ingest --carrier console --audit-ref <ref>`，已寫入 AT-965-9-2。
5. **事件欄位名依決策書**：`research.registry` 事件帶 `audit_ref`、`registry_sha256`（`SiReconcileService.scan()` 讀這兩欄；`SiReconcileService.java:119-120` 以 `kind` 與 `audit_ref` 辨識）。根層若改名，本檔 AT-965-6-3、7-1、7-5 的夾具同步改。
6. **主控裁決已落實（D-RR-11～18）**：`arxiv-agents` 的 URL 取 D-RR-16 逐字（契約 §5A.1 種子表）；`kind` 六值（`sitemap`、`search` 已獲裁決，根層同步加）；`src-registry` 12 字元；`registry_text`≤24576、外層檔≤65536 超界 422 不截斷。
7. **SI 狀態鍵名（D-RR-15）**：`status.items[0].research_fetch_max`（整數）與 `status.items[0].research_registry`（物件 `{seq, audit_ref, registry_sha256, watch_enabled}`，尚無同步＝null）；Console 以 `research_registry` 取最新已入帳者、以 `research.registry` 事件（必帶 `audit_ref`、`registry_sha256`，D-RR-14）掃已入帳 ref 集合；`research_fetch_max` 缺席時前端只顯示啟用數、不顯示警示；`research_registry` 缺鍵（根層未升版）視為讀不到、不當成從未同步。

### 7.3 已知邊界（不是待修缺陷）

- 並行同 digest 同步可能各落一列（§4）；對帳讀面標示即可。
- PATCH 停用路徑不做 24576 位元組大小閘（停用使快照多出 `disabled_*` 欄，可能超界；勘誤 E-3）：屆時同步端點回 422 `registry_too_large`、根層入帳拒收。使用者端處置＝重新啟用被停用的列以縮回快照，或停用／換掉 `extract` 較長的列。
- 追蹤來源與稽核檔只增不刪：E2E 與真機測試列只能停用、無法清除（設計）。
- 重新啟用被擋在「網域未開放」時，使用者須先到上方網域清單開放該網域（UI 以文案與停用鈕說明）。
- 被根層 `REG-STALE` 拒收而保留的稽核檔（Console 時鐘回撥或人工亂序入帳時才會發生）：Console 仍可能把它當成最新待入帳 P，當前登記恰等於 P 的 digest 時同步端點回 `unchanged`、狀態顯示待入帳，而鏡像停在已入帳的另一版。出口＝改動登記使 digest 不同再同步（新稽核檔 `time` 晚於最新已入帳者即可入帳）；被拒收的檔在 `si status` 的 Console 待入帳計數與巡邏日誌可見（QA2-03、QA2-05）。不設 force 端點（避免繞過單調性）。

---

## 📋 SCG-4 通過標準

- [ ] 74 個 AT 全數通過，輸出逐字貼入證據；本檔 §4.1 預期值改動恰等於實際改動（QA 以 `git diff` 核對，不多不少）
- [ ] 既有研究 AT 與 SI AT 零弱化（V4）；`ResearchReasonsTest` 零改動仍綠
- [ ] 黃金檔 G-R1、附錄 B golden 位元組與 sha 相符；G-S1 經根層 `consoleaudit.py` 驗簽收下
- [ ] `gradlew clean build`、Bridge `pytest` 與 `ruff check`（兩視角）、前端 lint／`tsc`／build／vitest 全綠（V5）
- [ ] 零 skip；零 `@Disabled`；零 `it.skip`
- [ ] RTM 本地子表回填（`AgentConsole/docs/06_quality/RTM-ResearchRegistry-20261110.md`，主控於 SCG-5 做）；`AgentConsole/docs/06_quality/RTM.md` 對應列回填
- [ ] 契約 §5A 與實作逐項校對後升 v1.0；Architecture 已知債登記

---

## 勘誤（本檔凍結之後的訂正；凍結前留空）

| 編號 | 日期 | 位置 | 原文 | 訂正 | 原因與證據 |
|------|------|------|------|------|------------|
| E-1 | 11-10 | AT-965-6-1 Then（約 L467） | 「緊湊、無 BOM、無結尾換行」 | 內文就地訂正為「緊湊、無 BOM、結尾恰一個 LF〔以附錄 C 為準，勘誤 E-1〕」 | 原文與附錄 C 及 G-S1 副本（結尾一個 LF）矛盾；以附錄 C 為準 |
| E-2 | 11-10 | AT-965-3 OpenAPI 文件化 AT（約 L455） | 「POST／PATCH 文件化 400／403／404／409／422／502／503／504」 | 內文就地訂正：POST 文件化 400／403／409／422／502／503／504；PATCH 文件化 400／403／404／422／502／503／504；409 只列 POST | `PATCH /research/watch-sources/{slug}` 只切 `enabled`、不撞 slug，無 409；契約同步訂正 |
| E-3 | 11-10 | §7.3 已知邊界（登記型；已在 §7.3 加一條） | 原文：無 | 登記：PATCH 停用路徑不做 24576 位元組大小閘（停用使快照多出 `disabled_*` 欄，可能超界）；屆時同步端點回 422 `registry_too_large`、根層入帳拒收。使用者端處置＝重新啟用被停用的列以縮回快照，或停用／換掉 `extract` 較長的列 | 實作輪發現的已知邊界，非待修缺陷 |
| E-4 | 11-10 | §4.1 說明（登記型；已在 §4.1 末加補註） | 原文：無 | 登記：`WATCH_OPS` 另立，不併入 `OPS`／`METHOD_KINDS` | 保留既有 20 方法鎖 |
| E-5 | 11-10 | §4.1 表外的既有測試同步（登記型） | 原文：§4.1 表無下列列 | 登記（預期值同步，非弱化）：ArchTest（`SiReadOnlyArchTest` GET 7→8、POST 6→7、si 方法 7→8、寫入埠加 `findRegistryWrites`；`IssueBridgeArchTest` 同）；`RbacIT.AT_960_5_3` 加兩條 matcher；`OpenApiIT.AT_950_10_1` SI path 清單加兩條；`ResearchSchemaMigrationIT` 的 V19／V22／守衛案例；Bridge `test_research_capability`（registry.py＝ro）；`test_si_readonly_lock`（普查 14→15）；`test_si_console_ingest.golden_problems`（排除 G-S1）；`test_si_export_differential::test_AT_932_1_E_2`（glob 排除 `*.audit.json`）；`research_pg_support.LAST_VERSION` 22→25；`test_research_router`／`orchestrator`／`db` 加四個種子 FETCH 網域 | 實作輪回報，主控裁決補入 |
| E-6 | 11-10 | 契約註記（登記型） | 原文：無 | 登記：`ResearchExceptionHandler.assignableTypes` 加 `SiController` | 同步取快照走研究面，否則 502／504 變 500 |
| E-7 | 11-10 | AT-965-9-5 Given 與 Then（約 L642、L644） | 「`research_fetch_max`、`research_registry`（`{seq, audit_ref, registry_sha256, watch_enabled}`」「`cases_version`、`cases_sha256`」「`prec_pm`、`rec_pm`、`contaminated`、`hit5_trend`」「`SI_STATUS_KNOWN_KEYS` 含 `research_fetch_max`、`research_registry`、`backtest`」「`research_registry.watch_enabled`」「`registry_sha256` 去 `sha256:` 前綴」「案例集 v`cases_version`」 | 內文就地訂正為 camelCase：`researchFetchMax`、`researchRegistry`（`watchEnabled`、`registrySha256`、`seq`、`auditRef`）、`backtest`（`casesVersion`、`casesSha256`、`hit3`、`n`、`contaminated`、`precPm`、`recPm`、`hit5Trend`） | backend `SiKeyNames.camelKeys` 把整棵樹轉 camelCase，前端實作用 camelCase 鍵；根層 SI status 仍是 snake_case，兩者以 Bridge／console-api 轉換相接 |
| E-8 | 11-10 | 前端 SI 寫入名單判定（登記型） | 原文：無 | 登記：前端不另判 SI 寫入名單，只判 ADMIN；名單外由 backend 回 403 `si_write_forbidden`，前端顯示原因、不重試（沿 P2b／P4） | 避免前後端名單分叉 |
| E-9 | 11-10 | commit 座標（登記型） | 原文：無 | 登記：根層規格 d7c1eeee、Console 規格 dfa55632、根層 RR 914e0adc、Console 實作 9e07a54e（原 ed0ee779 混入根層 45 檔，已以 reset --soft 拆回） | 追溯 |
| E-10 | 11-10 | AT-965-10-1（登記型；§2 規則本文不變） | 原文：AT 以 `test.skip` 處理 docker 缺席（實作面作法，違反 §2「不得新增 skip」） | 登記：已改為直接拋錯失敗（commit d0a750bd，SCG-4 QA4C-01） | §2 明定「Docker 缺席視為環境壞、直接失敗」 |
| E-11 | 11-10 | AT-965-10 群（新增 AT-965-10-3；§1 計數、§2 覆蓋表、§3 清單、§5 檢核同步 72→73） | 原文：無 AT 守 Bridge 映像的稽核目錄；NFR-RR-9 要求稽核目錄為全棧自帶容器卷 | 新增 AT-965-10-3（Bridge pytest 結構鎖）：`BRIDGE_SI_AUDIT_DIR` 必須在 `USER bridge` 之前被 Dockerfile `mkdir -p` 並 `chown bridge:bridge`；`engine-bridge/Dockerfile` 同步預建 `/si-audit`；AT 總數 72→73、Bridge 側 22→23、AC-965-10 3→4 | 真棧 E2E（AT-965-10-1）實跑：全新具名卷為 root 擁有、Bridge uid 10001 寫稽核檔 EACCES ⇒ 同步回 503（DEF-AC-036）；成因＝映像未預建該目錄，具名卷首次掛載繼承映像內擁有者 |
| E-12 | 11-11 | §6.2 V7（不是 AT；AT 總數不變） | 原文：「V7（掌舵者，目視）：研究來源設定對話框的版面與文案（國高中白話）；窄寬可用。」 | 改由代理截圖代驗：長駐棧 ADMIN 唯讀開啟對話框，1440／1000／375 三寬截圖、axe 無 serious／critical、無水平溢出、375 寬控制項可用、文案逐段對照國高中白話與規格用語；結果寫 RTM V7 列 | 掌舵者 2026-11-11 互動選項裁決「改用截圖代驗」（sid `58ce5ccd-13fb-47fc-8a46-b04fa73257d7`） |
| E-13 | 11-11 | 前端文案（AT 總數不變；AT-965-8-2、AT-965-8-3、AT-965-10-2 斷言補強，既有 AT-960-19-8 的來源字面預期同步） | 原文：對話框文案含未解釋的內部名詞與英文縮寫——來源欄「ENV 部署設定」「ADMIN 管理員新增」、間隔說明「Bridge 內建下限」、說明段「產業網域（Web 層）要先加進來…」、展開方式選項 `links`／`sitemap`、「網域未開放：請到上方網域清單開放 ＜主機＞」 | 訂正（只改顯示字；API 與送出值不變）：來源欄改「部署設定」「管理員新增」；間隔說明改「系統內建下限」；說明段第二句改為先解釋「Web 層」是什麼、再說要先加入至少一個產業網域；展開方式選項顯示「links（從這一頁的連結找文章）」「sitemap（從網站地圖找文章）」，值仍為 `links`／`sitemap`，清單表「展開設定」欄顯示不變；網域未開放訊息改「網域未開放，所以不會抓取：請到上方網域清單開放 ＜主機＞」。測試補強：AT-965-8-2 改整句精確比對；AT-965-8-3 釘選項顯示字與送出值；AT-965-10-2 加「網域表在可橫捲容器內、表寬不被擠壓」斷言 | V7 代驗（E-12）留下的白話文案建議，本輪發布前收掉；「375 寬網域表擁擠」查證後表格本來就在可橫捲容器內（屬設計），不改元件、補測試釘住；「殘留舊 INT 測試列」是長駐棧資料（已停用、不影響有效清單），產品不提供刪除，不屬程式修正 |
| E-14 | 11-11 | AT-965-10 群（新增 AT-965-10-4；§1 計數、§2 覆蓋表與 E 節、§3 清單、SCG-4 通過標準同步 73→74） | 原文：無 AT 以 ADMIN 視角掃自我進化頁的無障礙；AC-965-9 加的「研發工作流 → 研究來源設定」說明連結用主色小字 | 新增 AT-965-10-4（mock Playwright）：ADMIN 自我進化頁該連結可見且整頁 axe 無 serious／critical；`SiView.tsx` 連結文字色改用既有 token `text-wg-primary-strong`（對頁面底色對比 6.02）；AT 總數 73→74、Playwright 側 3→4、AC-965-10 4→5 | 全棧 E2E `self-improving-docker.stack.ts` 的 OBS_SI_321_UI 在全新拋棄式棧實跑抓到 `color-contrast` serious 一個節點（對比 4.21，低於 4.5；DEF-AC-039，P3）；成因＝既有 mock a11y spec 從未掃過 `/self-improving`，只在 ADMIN 渲染的連結沒被量到 |
