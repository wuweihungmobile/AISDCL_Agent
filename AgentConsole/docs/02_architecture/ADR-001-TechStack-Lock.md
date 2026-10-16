# ADR-001：AgentConsole 技術棧鎖定與架構決策（TechStack Lock）

| 項目 | 內容 |
|------|------|
| 狀態 | **ACCEPTED v1.0**（W1 凍結；變更須新增 ADR-00N 並引用本檔） |
| 建立日期 | 2026-10-14 |
| 決策者 | 掌舵者（主控）拍板；Architect＋SA（W1-A）整理並補充 |
| 適用範圍 | `AgentConsole/`（frontend、backend、engine-bridge、docker、docs） |
| 上位文件 | PRD `docs/01_requirements/Agent_ConsoleUI_PRD.md`（§0 權威）、UI 設計稿 README |
| 相關文件 | [Architecture.md](Architecture.md)、[RTM.md](../06_quality/RTM.md)、[Implementation_Plan.md](../04_planning/Implementation_Plan.md)、ADR-002（前端設計系統與圖表 spike 結果，由 W3 前端撰寫） |

---

## 1. Context（背景）

- PRD §3 版本註記要求：技術版本須於 SCG-2 架構凍結前定案並立 ADR；Tailwind 4 × Tremor 3 需 spike；Spring Boot 3.2 已近 EOL，鎖定時取當時 stable。
- repo 現況（PRD §0.1 實測，本輪未見反證）：web 程式碼為零（全新綠地）；AutoClaude、AISDLC_SDD 皆為純 CLI，無 HTTP server；PostgreSQL 18＋pgvector 與 AutoClaude 同映像。
- 本機工具鏈（W1-A 現查）：Java 21.0.11、Node 22.23.3、npm 10.9.9、Docker 29.6.1、uv 0.12.13；系統 `python3` 為 3.9.6（Bridge 必須用 uv 建 3.11 的 venv，不可用系統 python3）。
- 下一輪開發會切換到 **Windows 11 + PowerShell**（無 Bash 工具）：所有決策須同時考慮 Windows 可行性（見 D15）。
- 兩個外部事實由主控提供、本 ADR 作者未能獨立重現（對外連線被 auto mode 分類器拒絕）：Spring Initializr 預設 Spring Boot 4.1.1；Next.js latest 為 16.4.0。標為「主控回報」，並在 §6 設證據欄由 W2-A／W3 回填。

## 2. 決策總表

| 編號 | 決定 | 偏離 PRD？ | 待驗／待填 |
|------|------|-----------|-----------|
| D1 | Spring Boot 4.1.x ＋ Java 21 ＋ Gradle Kotlin DSL；不引入 QueryDSL | 偏離 §3.1 | 證據欄（§6 E-1） |
| D2 | Next.js 16 ＋ TypeScript 5 strict ＋ Tailwind 4 ＋ shadcn/ui ＋ lucide-react | 無（§3.1 一致） | npm 版本證據（§6 E-2） |
| D3 | 圖表：先 spike Tremor Raw，30 分鐘不成改 shadcn chart（Recharts）；不降 Tailwind | 偏離 §3.1 元件名 | spike 結果（ADR-002） |
| D4 | JWT 最小認證（登入／續期端點、users 放 `application.yml`）＋ SSE 以 fetch 串流帶 Bearer | 補充 §9.2；偏離 §3.2 圖示 | W2-A／W4 實測 |
| D5 | Flyway 擁有 DDL；Console 表全在 `console` schema；增補 V2／V3／V4 遷移 | 補充 §6.2 缺口 | `ddl-auto=validate` |
| D6 | ~~Engine Bridge 用自己的 venv~~ → **2026-10-15 改為裝進根層 `.venv`**（repo 單一 venv 規則，pre-commit stray_venv 閘否決自有 venv） | 無 | D6 補記 |
| D7 | engine-bridge 的 Docker build context 取 monorepo 根 | 偏離 §11.3 | W1-B／W2-B 實測 build |
| D8 | pause＝步驟邊界送 SIGTERM；resume＝重新 spawn；restore＝複製歷史 checkpoint；stop＝SIGTERM→30s→SIGKILL | 偏離 §0.2.2 | V-1、V-2（Architecture §12） |
| D9 | E2E 不連真 Claude／真 MiniMax；以 mock CLI＋Bridge 層 FakeBrain 驗證 | 無 | 相依 D-1（Plan） |
| D10 | `execution_runs` 欄位級寫入分工；Bridge 8 態寫 PG 時折成 PRD 6 態 | 補充 §0.2.2 | — |
| D11 | 視覺以設計稿 water_green 為準，PRD §8.2 深色方案不採用 | 偏離 §8.2 | ADR-002 |
| D12 | 匯入二段拆解；import signoff 只批准、confirm 才落庫 | 偏離 §7.1.4.1 回傳型別 | W3 後端落地驗證 |
| D13 | `autoclaude.dalBackend` 預設 FILE；Bridge 強制使用檔案型 checkpoint | 偏離 §5.5.1.5 預設值 | — |
| D14 | Compose／Infra 十二項調整（映像釘版、pgBackRest 改 apt、exporter、MinIO、profile 等） | 逐條標於 §3 D14 | W2-B 實測 |
| D15 | 跨平台（Windows 11 ＋ PowerShell）約束 | 補充 | Windows 接續檢查清單 |
| D16 | Redis 角色（**W7 D-19 改寫**）：只用於 refresh token 撤銷名單，Redis 不在線降級為單實例記憶體並記 WARN；限流計數與 SSE 消費位移**不使用 Redis**（原決定三項全列，實作時兩項從未用到，如實登記） | 補充 §11.2 | D23；降級測試見契約 §1.9.2 |

---

## 3. 逐項決策

### D1　Spring Boot 4.1.x（偏離 PRD §3.1：3.2.x）

- **Context**：PRD §3.1 寫 Spring Boot 3.2.x；§3 註記「3.2 已接近 EOL，建議升至 3.3+，鎖定時取當時 stable」。掌舵者回報：Spring Initializr 預設為 4.1.1，3.x 已不在 OSS 支援期（主控回報，證據欄見 §6 E-1）。
- **Decision**：Spring Boot **4.1.x**（初始以 Initializr 預設為準）＋ Java 21（Virtual Threads）＋ Gradle Kotlin DSL ＋ Spring Data JPA ＋ Flyway ＋ SpringDoc OpenAPI ＋ Spring Security（JWT）。**不引入 QueryDSL**，列表的動態條件一律用 Spring Data JPA `Specification`。
- **偏離 PRD §3.1，理由**：(a) PRD 自己授權「鎖定時取當時 stable、≥3.3」；(b) 新建專案不應從已停止 OSS 支援的主線起步；(c) QueryDSL 對 Spring Boot 4／Jakarta／Hibernate 的相容性未驗證，而 W2 任務書的依賴清單本就未列它。
- **Alternatives**：Spring Boot 3.5.x（最後一條 3.x 主線；依掌舵者回報已出 OSS 支援期）；3.3／3.4（已 EOL）；停在 4.0.x（4.1 已 GA，無理由落後）。
- **Consequences**：Spring Framework 7、Jackson 3（套件 `tools.jackson.*`）、Spring Security 7；`@MockBean` 改 `@MockitoBean`；starter 名稱一律以 Initializr 產物為準，**不憑記憶寫**；springdoc 版本以編譯通過者為準；jjwt 與 Jackson 3 的相容性由 W2-A 實測並寫入交卷；Testcontainers 需要 Docker daemon 在線。
- **Virtual Threads 的實際範圍（W7 補；完整性審查 L-03）**：PRD §3.1 的「Java 21，Virtual Threads」在本專案的落地只有**兩處**明確使用 `Thread.ofVirtual()`——SSE 寫出（`StreamConnection.java:64`，每條前端連線一條寫出執行緒）與 run 事件消費者（`RunConsumers.java:90`，每個活躍 run 一條讀 Bridge 串流的執行緒）。`backend/src/main/resources` 的 yml／properties 沒有設定 `spring.threads.virtual.enabled`（W7-QA 以 `jcmd <pid> Thread.print` 對執行中的 backend 實測：Tomcat 請求執行緒為 `http-nio-18080-exec-N` 平台執行緒，即 Spring Boot 4.1 在本專案設定下**預設不啟用**虛擬執行緒；QA_W7_Closure.md §6 L-03、觀察 O-32），所以 Tomcat 請求執行緒與 `@Scheduled`／`@Async` 目前是平台執行緒。若要全域啟用，另開決策並重跑壓力與釘選（pinning）檢查。

### D2　Next.js 16 ＋ Tailwind 4 ＋ shadcn/ui（與 PRD §3.1 一致）

- **Decision**：Next.js 16.x（App Router；主控回報 latest 為 16.4.0）、TypeScript 5（strict）、Tailwind CSS 4、shadcn/ui、lucide-react；Node 22 LTS；`next.config.ts` 設 `output: "standalone"`（Dockerfile 依賴）。
- **Alternatives**：降 Tailwind 至 3.4（PRD §3 備案）——否決：shadcn 與 Next 16 的現行預設即 Tailwind 4，降版拖累全站；圖表相容性改由 D3 處理。
- **Consequences**：Tailwind 4 為 CSS-first 設定（無 `tailwind.config.js`，用 `@theme`／CSS 變數）；設計稿 token 逐字搬進 `frontend/styles/tokens.css`；shadcn 元件以 token 覆寫視覺（見 D11）。

### D3　圖表：Tremor Raw 先 spike，shadcn chart 備援（偏離 PRD §3.1：Tremor 3.x）

- **Context**：PRD §3.1 指定 Tremor 3.x，但同節註記 Tremor 3 為 Tailwind v3 設計、與 Tailwind 4 未必相容，須 spike；失敗則降 Tailwind 或改相容圖表庫。
- **Decision**：W3 前端以 Tremor Raw（copy-paste 元件、可適配 Tailwind 4）先做一張 AreaChart，限時 30 分鐘；build＋render 通過 → 全站採 Tremor Raw；失敗 → shadcn `chart`（Recharts 底層）。**不降 Tailwind**。結果寫入 ADR-002 並回填 §6 E-3。
- **偏離 PRD §3.1，理由**：PRD §3 註記已授權以相容圖表庫替代；PRD §5.4.2「元件」欄的 `Tremor DonutChart／AreaChart…` 改以**圖表型別**為驗收依據，不以套件名為準。
- **Alternatives**：降 Tailwind（否決，見 D2）；直接 Recharts（等同備援）；手繪 SVG（設計稿原型所用，不可維護）。
- **Consequences**：RTM 的 `UI-KPI-*`、`UI-CHT-*` 驗收看「型別＋資料」；圖表需提供文字替代說明（`UI-A11Y-04`）。

### D4　JWT 最小認證與 SSE 認證方式（補充 PRD §9.2；偏離 PRD §3.2 圖示）

- **Decision**：Spring Security ＋ JWT（HS256）；access 30 分鐘、refresh 7 天；端點 `POST /api/v1/auth/login`、`POST /api/v1/auth/refresh`（RTM `API-AUTH-01／02`）；使用者清單放 `application.yml` 的 `console.auth.users[]`（admin／operator／viewer 各一組，bcrypt）；`JWT_SECRET` 環境變數必填（缺或短於 32 字元則啟動失敗）；無使用者管理 UI。前端 token 存 `sessionStorage`。
- **SSE 認證**：瀏覽器原生 `EventSource` 不能帶 `Authorization` 標頭 → 前端改用 fetch 串流（`@microsoft/fetch-event-source` 或等效自寫解析）帶 `Authorization: Bearer` 與 `Last-Event-ID`；**禁止把 token 放 query string**（會進 nginx access log 與瀏覽器歷史）。偏離 PRD §3.2 圖示的 `EventSource API`。
- **Alternatives**：Keycloak／OAuth2（過度）；Cookie session ＋ Redis（需另設 CSRF，且與 PRD「Bearer Token」衝突）；query-string token（洩漏風險）。
- **Consequences**：refresh token 的輪替與撤銷需要狀態，由 Redis 承擔（D16）；開發用預設密碼只寫在 backend README，正式環境必須替換。

### D5　Flyway 擁有 DDL、`console` schema、增補遷移（補充 PRD §6.2 缺口）

- **Decision**：
  1. Flyway 為 DDL 唯一擁有者：`V1__init.sql`＝PRD §6.2 逐字，前置 `CREATE SCHEMA IF NOT EXISTS console;`；`spring.flyway.schemas=console`、`default-schema=console`；JPA `hibernate.default_schema=console`、`ddl-auto=validate`。
  2. `V2__seed_system_configs.sql`：PRD §5.5.1.1～§5.5.1.6 六類參數預設（`apiKey`／`db_dsn` 類 `is_encrypted=true`、值留空）。其中 **`autoclaude.dalBackend` 預設值為 `FILE`**（見 D13，偏離 PRD §5.5.1.5 預設 `POSTGRESQL`）。
  3. Architect 增補（PRD §6.2 無對應表）：`V3__review_requests.sql`（Phase 4，持久化待審核項）、`V4__monitor_alerts.sql`（Phase 5，持久化告警與確認狀態）。欄位定義見 Architecture §11.3。
  4. `V5__seed_engine_configs.sql`（Phase 6）：補 PRD §0.6 權威校正要求但 §5.5.1 表未列的參數鍵（Claude CLI 指令與旗標、`enable_kernel_brain`、auto_resume 兩項、儲存後端 DSN 與雙讀策略），鍵清單見 Architecture §11.4。
- **Why schema**：AutoClaude 的 alembic 在 `public` 建了同名的 `projects`、`checkpoints` 等表；共用同一資料庫時，Console 表必須隔離。Bridge 的 SQL 一律寫 `console.<table>`（環境變數 `BRIDGE_DB_SCHEMA`，預設 `console`）。
- **Alternatives**：Hibernate `ddl-auto=update`（不可追溯、禁用）；JPA 擁有 DDL；Liquibase（PRD 未提）；與 AutoClaude 共用 `public`（撞名，否決）。
- **Consequences**：新增表一律走 Flyway 遷移並同步 RTM 的 `INF-DB-*` 列；`validate` 失敗＝實體寫錯，不是遷移錯。

### D6　Engine Bridge 自有 venv（🔴 2026-10-15 補記：被 repo 單一 `.venv` 規則否決——pre-commit 的 `tools/lib/stray_venv.py` 閘擋下 commit；改為 `VIRTUAL_ENV=<repo>/.venv uv pip install -e AgentConsole/engine-bridge`，`aisdlc-mock-claude` 落在根層 `.venv/bin`；主控以根層 venv 重跑 Bridge pytest：235 支通過／9 支略過。`tools/dev_start` 若重建 `.venv` 須重跑該安裝（把 engine-bridge 納入 bootstrap 依賴集＝Windows 輪待辦））

- **Decision**：Python 3.11＋FastAPI＋uvicorn＋psycopg 3；venv 位於 `AgentConsole/engine-bridge/.venv`，安裝 `-e . -e ../../AutoClaude`；**不使用根層 `.venv`**。
- **Why**：根層 `.venv` 服務 AutoSDD 的治理 harness（pre-push 等），共用會造成鎖版互踩；系統 `python3` 為 3.9，不可用。
- **Alternatives**：共用根 venv（否決）；僅容器內有 venv（本機開發需要，否決）；Poetry（repo 慣例為 uv）。
- **Consequences**：Windows 啟動 venv 為 `.\.venv\Scripts\Activate.ps1`；Dockerfile 以 pip 安裝；pid 存活判定與行程樹清理採 `psutil`（D15）。

### D7　Docker build context 取 monorepo 根（偏離 PRD §11.3）

- **Decision**：engine-bridge 服務 `build.context` 指向 monorepo 根（compose 在 `AgentConsole/`，故為 `..`），`dockerfile: AgentConsole/engine-bridge/Dockerfile`；映像內 `COPY AutoClaude/` 與 `COPY AgentConsole/engine-bridge/`，並 `pip install` 兩者。AISDLC_SDD 以唯讀 bind mount（`../AISDLC_SDD:/engines/aisdlc_sdd:ro`），Bridge 以 `SDD_ROOT` 指向 LATEST。
- **偏離 PRD §11.3，理由**：PRD 寫 `context: ./engine-bridge` 並以 volume 掛載 `../AutoClaude`，映像因此不自足、不可重現；且 PRD 寫死的 `AISDLC_SDD_v0.14` 已過期（LATEST 現為 v0.30，**一律現查**：`python AISDLC_SDD/scripts/sdd_version.py`）。
- **Alternatives**：在 `AgentConsole/` 複製一份 AutoClaude（雙份漂移，否決）；執行期 `pip install -e` 掛載原始碼（不可重現，否決）；發布到私有 index（過度）。
- **Consequences**：build context 為整個 monorepo，必須有忽略清單（BuildKit 支援與 Dockerfile 同目錄的 `Dockerfile.dockerignore`，放 `engine-bridge/`；排除 `.git`、`**/node_modules`、`**/.venv`、`AISDLC_SDD`）；映像內 AutoClaude 版本＝建置當下的工作樹，升級需重建。

### D8　pause／resume／restore／stop 語意（偏離 PRD §0.2.2）

- **Decision**（不改 AutoClaude，NFR-COMPAT-01）：

| 操作 | 語意 |
|------|------|
| pause | Bridge 設旗標；**步驟邊界**由引擎日誌的「下一個步驟的啟動行」判定（W1-B 對真引擎實證：引擎本身**不寫步驟級 checkpoint**，故不能靠 checkpoint 檔變化偵測）；一到邊界即終止引擎整棵行程樹，並由 Bridge 以引擎自己的 `FileStateRepository` 寫入 checkpoint → 狀態 PAUSED |
| resume | 僅 PAUSED 可用；不帶 `--fresh` 重新 spawn，引擎自行從 checkpoint 的 `step_idx` 續跑 |
| restore | PAUSED 或終態皆可用：把指定歷史 checkpoint 寫回成現用 checkpoint 再 spawn（終態已放的鎖須重新取得，可能 409） |
| stop | 終止行程樹（POSIX SIGTERM、Windows `terminate()`）；逾 30 秒升 SIGKILL（`kill()`）→ CANCELLED |

> 上表第一列的「引擎不寫步驟級 checkpoint」是 W1-B 於 2026-10-14 對真引擎的實證結論（見其 `runner.py`、`logparse.py`、`checkpoints.py` 檔頭自述），**修正了任務書原先的假設**（「AutoClaude 每步結束會原子寫 checkpoint 檔」）；最終以 W1-B 交卷與其 pytest 為準。

- **偏離 PRD §0.2.2，理由**：PRD 寫「pause 不殺子程序，等步驟自然結束」；實際上引擎一次跑完整份 Playbook，沒有「步驟邊界自然結束」這個點，也沒有暫停鉤子。ESC＋F12 熱鍵不可用——`main.py::register_global_hotkey` 在無 TTY 或無人值守時略過註冊。
- **前提約束**：pause／restore 的 checkpoint 由 Bridge 以引擎的 `FileStateRepository` 讀寫**檔案**，故 Bridge 必須強制 `storage.mode ∈ {yaml_only, both}`（見 D13）。
- **Alternatives**：改 AutoClaude 加暫停鉤子（違反零侵入）；SIGSTOP／SIGCONT（不可攜 Windows、PTY 語意不明）；stdin 注入熱鍵（TTY 依賴）。
- **Consequences**：邊界是在「下一個步驟已啟動」之後才判定，所以被終止的是剛啟動的下一步驟（含其 claude 子行程），resume 會從 checkpoint 的 `step_idx` **重做該步**（at-least-once，步驟需可重入）；Windows 的 `terminate()` 是強制結束（無優雅關閉語意），但 checkpoint 由 Bridge 在引擎終止**之後**才寫入，故不受影響；行程樹須先以 psutil 快照再逐一終止，否則 claude 子行程會變孤兒（D15）；引擎自身的 Token Guard halt 與 ESCALATION，目前由 Bridge 判為 FAILED（reason 分別帶「halted」與「引擎升級（ESCALATION）」，並發 `alert` 事件）；人工續跑走 `restore`（Bridge 的 restore 接受終態 run）；以 W1-B 交卷為準（V-3、V-4）。

### D9　E2E 策略：不連真 Claude／真 MiniMax

- **Decision**：
  1. 步驟執行：`claude.command` 指向 mock CLI（`AutoClaude/tests/fixtures/dummy_cli.py`，或 W1-B 自備的 mock；以其交卷為準），playbook 各步用 `command:`。注意 `dummy_cli.py` 的授權提示對**任何指令**都有 60% 機率觸發（`needs_auth = cmd in AUTH_REQUIRED_CMDS or random.random() < AUTH_RANDOM_PROB`），非只限 `step2`／`step3`；是否被 `loop.auth_patterns` 自動應答須實測，flaky 時改用無隨機的 mock。
  2. Console 驅動的 E2E：console-api 設定 `console.execution.mock-cli=true`（預設 false，profile `e2e` 開啟），由 `PlaybookBuilder` 補 `command` 與 `expected_output_regex`、並在 `config_overrides` 設 `claude.command`；Bridge 不認識 mock，維持純轉送。
  3. Brain：`AutoClaude/tools/mock_brain_server.py --port 9100` 只涵蓋 correction／goal／evolution 三型，**不支援 decomposition**（實證：該檔搜尋 `decompos` 零命中）。decompose 以 Bridge 層 FakeBrain 單元測試覆蓋；跨三層真鏈的 decompose E2E 需要 Bridge 提供 FakeBrain 注入點（建議 `BRIDGE_FAKE_BRAIN=1`），登記為 Plan 相依 D-1。
  4. 真 Claude 只留給掌舵者手動驗。
- **Alternatives**：錄製回放真模型（成本與漂移）；Bridge 內建 mock 模式覆寫任務（讓 console 路徑與生產不同，否決）；擴充 `mock_brain_server.py`（動 AutoClaude，違反零侵入）。
- **Consequences**：Docker 映像不含 Claude Code CLI，Docker 全棧預設走 mock；真 Claude 只在「Bridge 本機執行且 PATH 有 `claude`」的本機開發模式可用。

### D10　`execution_runs` 寫入分工與狀態映射（補充 PRD §0.2.2）

- **Decision**：console-api 只在建立時寫 `id, project_id, run_number, autonomy_level, scope, token_budget, dag, started_at`（`status` 初值由 DDL default `INITIALIZING` 帶入，非顯式寫入）；Bridge 擁有 `status, subprocess_pid, bridge_instance, advisory_lock_key, total_tokens_used, completed_at`，以及 `execution_steps`、`checkpoints` 兩表的全部寫入；console-api 對這些欄位只讀。Bridge 8 態寫入 PG 時折成 PRD 6 態：PAUSING→RUNNING、CANCELLING→RUNNING。
- **補償**：Bridge 建立失敗（409／422／逾時）時，console-api 刪除剛建立的 `execution_runs` 列（僅限 `status=INITIALIZING` 且 `subprocess_pid IS NULL`）並回傳對應錯誤。
- **Alternatives**：雙方皆可寫（雙寫漂移，PRD §0.2.2 禁止）；只由 console 寫（pid／lock 由 Bridge 才握有，console 掉線即失真）。
- **Consequences**：欄位級所有權需測試保護（console 端實體對 Bridge 欄位標 `updatable=false`；Bridge 端 SQL 只 UPDATE 其欄位）；詳見 Architecture §7。

### D11　UI 視覺以設計稿為準（偏離 PRD §8.2）

- **Decision**：採設計稿 water_green（淺色、扁平、主色 `#498428`、Inter＋Noto Sans TC＋JetBrains Mono、Lucide 線性圖示、8pt grid、無陰影、強制焦點環）；深色模式本輪不做。
- **偏離 PRD §8.2，理由**：設計稿為後交付的像素級定稿，掌舵者指定為 UI 唯一真相源；PRD §8.2 的 Slate／Indigo 深色方案與之衝突。PRD §8.2 動畫表降為參考，以設計稿 Motion 規範為準。
- **Consequences**：設計稿中的 emoji 一律以 Lucide 圖示或色點取代；詳細落地決策與圖表 spike 結果見 ADR-002（W3 撰寫）。

### D12　匯入拆解與 signoff／confirm 語意（偏離 PRD §7.1.4.1 回傳型別）

- **Context**：Bridge `decompose` 回傳扁平的步驟 DAG（`playbook.tasks[]`），不是「專案→目標→任務」三層；PRD §7.1.4 的 `confirm` 與 §7.1.4.1 的 import `signoff` 皆寫回 `ProjectResponse`，語意重疊；設計稿流程是「先 signoff 審批、再按確認匯入」。
- **Decision**：
  1. 規格凍結偵測：呼叫端提供 `specDir` 且 `GET /sdd/fsm/{project}` 顯示已凍結 → 走 `POST /sdd/compile`；否則走 decompose。預設為 decompose。
  2. decompose **二段拆解**（皆走 `POST /autoclaude/decompose`，每次呼叫各受三道有界閘）：段一以文件全文為 `goal` → 回傳步驟映射為 Goals；段二對每個 Goal 以「Goal 名稱＋說明」為 `goal` 再拆 → 回傳步驟映射為 Tasks。任一次 422 以結構化錯誤顯示（不截斷、不自動修剪，US-I-10）。
  3. 草案以 `import_records.parsed_result` 保存（含各次呼叫的 `draft_id` 與 `signed_off=false`）。
  4. **import `signoff`**：`approver` 必填非空（否則 400）→ 對各 `draft_id` 呼叫 Bridge `:approve`（審計）→ 設 `import_records.signed_off/by/at`；回傳 `ImportRecordResponse`。**`confirm`**：要求已 signoff（否則 409）→ 單一交易建立 Project／Goal／Task（`signed_off=true`，承襲 approver 與時間）→ 回傳 `ProjectResponse`（201）。
  5. 專案／目標／任務層級的 signoff 端點照 PRD 提供；草案旗標 `draft`（建立請求選填、預設 false）供 AI／外部程式與 E2E 造出 `signed_off=false` 的資料。
- **偏離 PRD §7.1.4.1，理由**：若 signoff 即落庫，`confirm` 就失去存在意義；兩步分工與設計稿一致，也避免兩個端點各建一次專案。
- **Alternatives**：只做一段拆解（Goal 全擠成一個，失去多目標價值）；signoff 即落庫並廢掉 confirm（與設計稿流程衝突）。
- **Consequences**：parse 對 Bridge 呼叫 1＋N 次（N＝Goal 數，≤24），耗時由 UI「解析中」呈現；Bridge 把草案存成 `<workspace>/_drafts/<draft_id>.json`（W1-B `decompose.py` 檔頭自述，重啟後仍可 approve）；workspace 被清掉時 `:approve` 回 404 → console 回 409 並提示重新解析；對已簽署的草案再 `:approve` 會回 409 `already_signed_off`，console 視為成功（冪等重試）。

### D13　引擎 DAL 預設與 checkpoint 檔依賴（偏離 PRD §5.5.1.5）

- **Decision**：`autoclaude.dalBackend` 預設 `FILE`（對映 `storage.mode=yaml_only`）；`POSTGRESQL` 對映 `both`（File 主寫＋PG 影子，checkpoint 檔仍存在）；`IN_MEMORY` 不支援 pause，降為 FILE 並審計；**Bridge 拒絕 `db_only`**。
- **偏離 PRD §5.5.1.5，理由**：pause／restore 靠 Bridge 讀寫的 checkpoint 檔；`db_only` 沒有檔，D8 無法成立。`both` 需要 `AUTOCLAUDE_DB_DSN` 與已遷移的引擎 schema，不應成為開箱預設。
- **Alternatives**：預設 `POSTGRESQL`（開箱即需 alembic 遷移，E2E 變重）；用 PG 輪詢取代檔案偵測（需改引擎寫入時機）。
- **Consequences**：引擎狀態（引擎自己的 schema）與 Console 讀模型（`console` schema，由 Bridge 寫入）是兩份資料，彼此不是備份關係；NFR-OBS-01 的「四源一致」抽查須分別比對。

### D14　Compose／Infra 調整（逐條標「偏離 PRD §x，理由」）

| # | 調整 | 偏離／補充 | 理由 | 來源 |
|---|------|-----------|------|------|
| 1 | engine-bridge context 取 monorepo 根 | 偏離 §11.3 | 見 D7 | W2-B 任務書 |
| 2 | pgbackrest 映像改用 `apt-get` | 偏離 §11.4.3 | PRD 以 `apk add` 安裝，但 `pgvector/pgvector:pg18` 為 Debian 基底（W2-B 任務書陳述，待其實證） | W2-B |
| 3 | 主節點自建映像含 pgbackrest；`archive_command` 同時 `cp` 與 `pgbackrest archive-push` | 偏離 §12.2.2 | `cp` 供 replica 的 `restore_command`，`archive-push` 供 PITR | W2-B |
| 4 | 離站 repo2 預設指向 compose 內 MinIO（真 S3 只改 `.env`） | 補充 §12.3.2 | PRD 允許 S3／MinIO；使離站備份可在本機驗證 | W2-B |
| 5 | 追加 `postgres-exporter-primary／replica`、`minio`、`minio-init` | 偏離 §11.2（11→15 個） | §12.6.1 引用 exporter 卻未列服務 | W2-B |
| 6 | Replica 空資料目錄時由 entrypoint 自動 `pg_basebackup -R` | 補充 §12.2.6 | PRD 手動腳本不在 replica 容器內，且 `postgresql.conf` 不展開環境變數 | W2-B |
| 7 | profiles：`db`（預設）／`app`／`full`（nginx） | 補充 §11.3 | 資料庫層可單獨驗證 | W2-B |
| 8 | 映像一律釘版本，不用 `latest` | 偏離 §11.2 | 可重現 | W2-B |
| 9 | **nginx 同時加入 backend-net** | 偏離 §11.3 | PRD 只給 frontend-net，而 backend 只在 backend-net／db-net，nginx 解析不到 `backend`（Docker DNS 只解析共用網路上的服務） | Architect 新增 |
| 10 | **pgadmin 加入 backend-net；全棧模式 PG 不對 host 發布，本機開發由 dev compose 發布** | 偏離 §11.3 | `db-net` 為 `internal: true`，只掛在它上面的容器其 `ports:` 對 host 不可達（**待 W2-B 實測**：`docker compose` 起來後對 5050／5432 做連線測試） | Architect 新增 |
| 11 | 刪除 `docker compose exec backend java -jar app.jar --spring.flyway.enabled=true` | 偏離 §11.7 | Flyway 隨 Spring Boot 啟動自動執行；該指令會在容器內另起一個應用實例 | Architect 新增 |
| 12 | `NEXT_PUBLIC_API_URL` 語意＝後端 origin（不含 `/api/v1`），Docker 同源時為空字串 | 偏離 §11.6 | PRD 寫 `/api` 會與路徑 `/api/v1/...` 疊成 `/api/api/v1` | Architect 新增 |
| 13 | Prometheus 保留期 15d→**35d**（`--storage.tsdb.retention.time=35d`） | 偏離 §11.3 | 可用性 SLO 的 `ratio_30d` 要有完整 30 天原始樣本才名實相符；15d 時它實際只涵蓋 15 天 | W7-INFRA（D-14） |
| 14 | 新增具名卷 `prometheus_data`（掛 prometheus 的 `/prometheus`；卷總數 11→12） | 偏離 §11.3（卷清單未列） | `down` 或重建容器後仍接得上，SLO 的 30 天歷史才不會歸零；`down -v` 才會清掉 | W7-INFRA（D-14） |

- **Consequences**：#9～#12 為 Architect 新增，W2-B 須實測確認並回寫 `docker/README.md` 〈與 PRD 的差異〉；compose 最終服務、埠、卷以 `docker compose config` 輸出為準，並回填 Architecture §2。

### D15　跨平台（Windows 11 ＋ PowerShell 接續）

- **Decision**（來源：掌舵者 2026-10-14 的跨平台補充；本 ADR 補 psutil 與 gradlew 衝突）：
  1. 文件中每段指令皆為 bash＋PowerShell 雙區塊；PowerShell 不用裸 `cd`／`Set-Location`（用 `Push-Location …; …; Pop-Location` 同行成對）、不用 `VAR=value cmd` 前綴（用 `$env:VAR="value"; cmd`）、讀 rc 不接管線。
  2. Bridge 須能在 Windows 執行：結束子程序一律 `proc.terminate()`／`proc.kill()`；`signal.SIGTERM` 等名稱須包 `if sys.platform != "win32"`；Windows spawn 帶 `creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)`；**pid 存活與行程樹清理採 `psutil`**（`psutil.pid_exists()`、`Process.children(recursive=True)`；W1-B 若採 ctypes 須於交卷聲明，主控回寫本條）；路徑比對 `Path.resolve()` 後再 `os.path.normcase()`；寫檔為「寫新檔→（`try/except OSError`）replace」；不用 `fcntl`、`os.fork`、`pty`、unix socket。
  3. Shell 腳本只給容器內（Linux）用；主機側操作用 `docker compose …` 或提供 `.ps1` 對等版（`.ps1` 必須 CRLF；含非 ASCII 加 UTF-8 BOM）。PRD §12.3.4 的 `restore.sh` 與 §12.5.2 的 failover 腳本是**主機側**腳本（內部呼叫 `docker compose`）：W2-B 須改成容器內執行（`docker compose run --rm pgbackrest …`）或補 `.ps1`。
  4. Git 層：`gradlew`（LF）與 `gradlew.bat`（CRLF）皆入庫。
  5. 路徑字面不寫死任何磁碟絕對路徑（例如 macOS 使用者家目錄下的路徑）。
- **🔴 已知衝突（須主控裁決）**：掌舵者的跨平台補充要求 `gradlew` 索引模式為 100755，但根層 `tools/tests/test_platform_neutral_paths.py` 的 exec bit 鎖要求「索引內的 100755 只准落在 `ONBOARDING.md` §6 粗體跨度『755 入庫範圍』之內」。`AgentConsole/backend/gradlew` 以 100755 入庫會讓根層全套轉紅，除非同一個 commit 把該路徑補進 ONBOARDING §6 的粗體跨度。二擇一：① 補進跨度；② `gradlew` 以 644 入庫，文件一律寫 `sh gradlew` 與 `.\gradlew.bat`。本輪文件的 bash 區塊寫 `./gradlew`，並註明 Permission denied 時改 `sh gradlew`。
- **Consequences**：Windows 上 `terminate()` 不是優雅信號，stop 的「SIGTERM→30 秒→SIGKILL」退化為立即結束；Bridge 測試套件須在 Windows 全套實跑（見 Implementation_Plan〈Windows 接續檢查清單〉）。

### D16　Redis 的角色（補充 PRD §11.2「快取／Session 儲存」；**W7 主控裁決 D-19 改寫，2026-10-16**）

- **現況（完整性審查 I-06，W7 查證）**：原決定列了三個用途，**實作時全部沒有做**：後端的 `build.gradle.kts` 與 `application*.yml` 沒有任何 Redis 相依或設定；限流是 Bucket4j 記憶體實作（契約 §0.4 第 4 點）；SSE 位移存資料庫（`execution_runs.console_last_seq`，Flyway V7）；Bridge 探測環形緩衝在記憶體（`BridgeHealthMonitor`）；登出只清瀏覽器 session。但 compose 仍把 `SPRING_DATA_REDIS_HOST／PORT` 傳給 backend、並要求 redis healthy 才啟動 backend，也就從來沒有 D16 承諾的「Redis 不在線仍可用」降級測試。
- **Decision（改寫）**：Redis 為**選配**，本輪**只實作原三項中最有價值的一項**——**refresh token 撤銷名單**：換新輪替與登出時撤銷舊 token（鍵＝`jti`，存活到該 token 的 `exp`），**Redis 優先；Redis 不在線時降級為單實例記憶體名單並記 WARN**（D16 原本的降級承諾，現在才有實作與測試）；新增 `POST /api/v1/auth/logout`（契約 §1.9；細節與取捨見 D23）。**限流計數（每分鐘 100 次，NFR-9.2-06）維持 Bucket4j 記憶體實作、SSE 消費位移維持資料庫**，兩項列為「**未使用 Redis**」，文件不再宣稱它們用 Redis。
- **原決定（v1.0，保留供追溯）**：「Redis 為選配加速層，Phase 1／2 不依賴：(1) refresh token 輪替與撤銷名單；(2) Rate Limit 計數（每分鐘 100 次，NFR-9.2-06）；(3) console-api 消費 Bridge SSE 的位移（`console:run:{runId}:last_seq`）與短期重播緩衝。本機開發未起 Redis 時退回記憶體實作（僅單實例有效）。」
- **Alternatives**：不用 Redis（JWT 無狀態則無法撤銷）；改存 PostgreSQL（可行，但 PRD 已配置 Redis）；三個用途都做（否決：限流與 SSE 位移沒有分散式需求，Console 目前單實例，做了只增加相依與失效面）；移除 compose 的 Redis（需 INFRA 另案，見後果）。
- **Consequences**：後端新增相依 `spring-boot-starter-data-redis`（契約附錄 D.4）；**必須設 `management.health.redis.enabled=false`**（否則 Redis 不在線會讓 `/actuator/health` 變 DOWN，降級承諾落空）；`SPRING_DATA_REDIS_HOST／PORT` 改為選填（契約附錄 D.2）；`docker-compose.dev.yml` 的 redis 維持選配；**compose 仍要求 redis healthy 才啟動 backend**（`docker-compose.yml` 的 `depends_on`），降級只保護**執行期**的 Redis 中斷、不保護冷啟動——主控裁決維持不動（契約 §6.7.3 Q6）。Architecture §6(c)、§6(d)、§8.1、§8.6、§9.4 的 Redis 字樣已同步訂正。

---

## 4. 偏離 PRD 清單（彙總，供 QA 核對）

| 偏離 | PRD 位置 | 決策 |
|------|----------|------|
| Spring Boot 3.2.x → 4.1.x；不用 QueryDSL | §3.1 | D1 |
| Tremor 3.x → Tremor Raw／shadcn chart | §3.1 | D3 |
| EventSource → fetch 串流帶 Bearer | §3.2 | D4 |
| Dark Mode 為主 → water_green 淺色 | §8.2 | D11 |
| pause 不殺子程序 → 步驟邊界 SIGTERM＋重新 spawn | §0.2.2 | D8 |
| engine-bridge context／掛載方式、SDD 版本 v0.14 | §11.3、§0.1 | D7 |
| pgbackrest 映像、archive_command、exporter、MinIO、profile、釘版、網路與埠、Flyway 手動步驟、`NEXT_PUBLIC_API_URL` | §11.2～§11.7、§12.2～§12.6 | D14 |
| import signoff 回傳型別 | §7.1.4.1 | D12 |
| `autoclaude.dalBackend` 預設值 | §5.5.1.5 | D13 |
| US-I-05 驗收字樣「支援瀏覽按鈕」不提供（以路徑輸入＋allowlist 驗證取代） | §5.2.3 | G-15 |
| KPI「專案完成率」「目標達成率」的「環形進度圖（Tremor DonutChart）」→ 設計稿畫面 8 的數值卡＋delta（W5 主控裁決 C-13，2026-10-15） | §5.4.2 | D11；G-20 |
| PRD §5.3.2「等級 6-10 含自動突變、自演化」與 §5.5.1.2 兩個旗標的字面期待 → 引擎現況只有 Brain 逐步校正（對映 `minimax.enable_kernel_brain`），自演化只產生提案、不套用，`playbook.max_evolutions`／`require_evolution_signoff` 在生產路徑沒有讀者；Console 如實回報 `engineCapabilities`，`agent.enableSelfEvolution` 標 `STORED_ONLY`（W7 主控裁決 D-11，2026-10-16；證據表＝契約 §6.6.2） | §5.3.2、§5.5.1.2 | D20 |
| 設計稿 water_green 色票用作**文字**時對比不足（text-muted 3.78:1、accent／error／warning／secondary 當文字 3.1～3.6:1，QA DEF-AC-004）→ `frontend/styles/tokens.console.css`〈無障礙覆寫〉加深文字色並新增 warning-text／secondary-text／terminal-* 四個文字專用色，達 WCAG 2.1 AA 4.5:1；設計稿原值仍在 `tokens.css` 逐字保留、主色 `#498428` 與區塊底色不動（W5 主控裁決 C-18，2026-10-16；axe 閘 `tests/e2e/a11y.ts` 釘住，設計若改色票須同時過閘） | §8.2、§8.4 | D11；DEF-AC-004 |
| **FSM 狀態不走 SSE，改由 console-api 對 Bridge 的 `GET /sdd/fsm*` 做 30 秒輪詢**（PRD §0.2「SSE 推 log＋ExecutionObservation＋FSM 狀態」；FSM 檔只在 SDD runtime 執行時才變動，Bridge 事件型別只有六種、沒有 FSM 事件；W7 主控裁決 D-16，2026-10-16） | §0.2 | D22 |
| **`POST /decompose` 以 AutoClaude `GoalDecomposer` 為唯一分解器，SDD 規格走路徑 A（`/sdd/compile`）編譯**；不另建「呼叫 SDD skill」的分解路徑（PRD §0.2「`POST /decompose` 呼叫 GoalDecomposer／SDD skill」；Bridge `decompose.py` 只用 GoalDecomposer；W7 D-16） | §0.2 | D22；契約 §3.3.2 |
| **signoff 與 SDD `HUMAN_PENDING` 只做語意對映：Console 只讀 FSM-STATE、不回寫**（PRD §0.4／US-I-09「signoff 對應 SDD HUMAN_PENDING」；Console 的 signoff 只寫自己的表與 GoalDecomposer 的 `:approve`；回寫 FSM-STATE 會繞過 SDD FSM runtime 的不變量——AISDLC_SDD Rule 9「繞過 `FSMRuntime` 直接讀寫 `FSM-STATE-*.yaml`」是違反即停機的禁令；W7 D-16） | §0.4、§5.2.3 US-I-09 | D22 |
| **前端測試覆蓋率「≥ 70%」的量測口徑**：只量 `frontend/vitest.config.mts` 的 `coverage.include`（31 個項目、其中 2 個是 glob：API client／auth store／狀態表／格式化／表單驗證與錯誤對應／匯入與設定的邏輯層／SSE 與即時狀態／Markdown 元件／四區塊版面／少數 UI 原子）；整頁視圖與卡片（`components/domain/**` 的頁面檔、`app/**` 路由、`components/ui` 與 `components/charts` 的其餘檔）由 Playwright E2E 驗證、**不計入**；門檻 lines／statements／functions 70、**branches 60**（低於 PRD 的 70）。QA 報告的前端覆蓋率數字就是這個子集的數字；**全量覆蓋率未量**（W7 完整性審查 V-07，主控裁決保留，2026-10-16） | §9.4（NFR-9.4-02） | G-21 |
| **Prometheus 保留期 15d → 35d**（`--storage.tsdb.retention.time=35d`）：可用性 SLO 的 `ratio_30d` 要有完整 30 天原始樣本才名實相符，15d 時它實際只涵蓋 15 天（W7-INFRA，D-14） | §11.3（compose 的 prometheus 服務） | D14 追加 #13 |
| **新增具名卷 `prometheus_data`**（掛在 prometheus 的 `/prometheus`）：`down` 或重建容器後仍接得上，可用性 SLO 的 30 天歷史才不會歸零；PRD §11.3 的卷清單沒有它（W7-INFRA，D-14；Architecture §2.5，卷總數 11→12） | §11.3 | D14 追加 #14 |

## 5. PRD 缺口與矛盾登記

| 編號 | 位置 | 問題 | 處置 |
|------|------|------|------|
| G-01 | §11.3 | nginx 與 backend 無共用網路 | D14-9 |
| G-02 | §11.3 | `db-net internal` 與發布埠矛盾 | D14-10（待驗） |
| G-03 | §11.4.3 | pgbackrest `apk` 對 Debian 基底 | D14-2 |
| G-04 | §12.6.1 | 引用未定義的 exporter 服務與 `pgbackrest_*` 指標來源 | D14-5；pgbackrest 指標的產出方式由 W2-B 決定並寫入 `docker/README.md` |
| G-05 | §11.7 | 手動 Flyway 指令多餘 | D14-11 |
| G-06 | §12.2.4／§12.2.6 | replica 設定檔不展開環境變數；腳本位置與執行處不符 | D14-6 |
| G-07 | §11.6 | `NEXT_PUBLIC_API_URL` 疊成 `/api/api/v1` | D14-12 |
| G-08 | §6.2 | 無 review 與 alerts 持久化表 | D5（V3／V4） |
| G-09 | §7.1.4／§7.1.4.1 | confirm 與 signoff 語意重疊 | D12 |
| G-10 | §5.3.2／§5.3.6 | 審核閘需要引擎支援，AutoClaude 無審核鉤子 | Architecture §6(c)：console-api 提前一步 pause；待驗 V-4 |
| G-11 | §5.2.4 | AI 輸出為三層 JSON，而 GoalDecomposer 輸出為扁平步驟 | D12 二段拆解 |
| G-12 | §5.3.2／§5.5.1.2 | 並行設定與引擎序列執行矛盾 | Architecture §12 L-1（只儲存、不生效） |
| G-13 | §5.4.2／§5.4.5 | PRD 指標卡與設計稿的指標卡不同（設計稿四張、PRD 八張） | 兩者皆實作：Dashboard 與 Monitor 頁依設計稿版型，PRD 八項 KPI 全數提供（`UI-KPI-*`） |
| G-14 | §5.1.4 | 建議元件 `@uiw/react-md-editor` 對 React 19／Next 16 的相容性未知 | W3 實測；不通過則改 `react-markdown`＋`remark-gfm`＋自建 Split View，並寫入 ADR-002 |
| G-15 | §5.2.3 US-I-05 | 驗收寫「支援瀏覽按鈕」，但瀏覽器無法瀏覽伺服器檔案系統，PRD §7 也沒有目錄瀏覽端點 | 不提供瀏覽；以路徑輸入＋Bridge allowlist 驗證滿足（偏離驗收字樣，RTM `US-I-05` 以此為準） |
| G-16 | §7.1.5／§5.4.5 | 缺「列出專案執行批次」端點，但設計稿監控頁有「執行批次」下拉、US-M-06 要批次比較；監控端點也沒有 `runId`／時間範圍參數 | 補 `GET /api/v1/projects/{projectId}/executions`（`API-EXE-14`）與監控端點的 `runId`／`from`／`to` 查詢參數 |
| G-17 | 設計稿頂列 | 通知鈴與 signoff 佇列徽章需要跨專案計數，PRD 無端點 | 補 `GET /api/v1/notifications/summary`（`API-NTF-01`） |
| G-18 | §5.4.3 US-M-08／M-10 | 自訂儀表板版面無後端欄位；「資源使用情況」在 Bridge 契約中沒有 CPU／記憶體欄位 | 版面存前端 `localStorage`；Agent 狀態以連線、當前任務、Token 與步驟進度呈現。**資源使用情況已於 W7 補上（D21，2026-10-16）**：Bridge `resources`（psutil 取樣引擎行程樹）→ `bridge.resources` → Agent 即時狀態卡 |
| G-19 | §5.1.3 US-T-02 | 驗收要「執行歷史」，Task DTO 無對應欄位 | 補 `executionHistory`（由 `execution_steps` 依 `task_id` 衍生；Phase 2 為空清單，Phase 4 起為真資料，契約 E2E-03 步驟 8 驗兩筆） |
| G-20 | §5.4.2 UI-KPI-01／02 | KPI「專案完成率」「目標達成率」PRD 寫「環形進度圖」（Tremor `DonutChart`），設計稿畫面 8 只有數值卡與 delta；W4 實作依設計稿畫數值卡，QA 因 PRD 字樣把兩列留在 🟡 | **以設計稿畫面 8 的數值卡為準**（依據 D11「視覺以設計稿為準」；本列把它落到 KPI 這兩列，並同步登記於 §4 偏離清單）：兩張卡以數值＋delta 呈現，資料來源 `projectCompletionRate`／`goalAchievementRate`（契約 §1.3.1）；RTM `UI-KPI-01`／`UI-KPI-02` 改 `✅ 已驗證`（W5-QA，主控裁決 C-13，2026-10-15）；PRD §5.4.2 對這兩列的「環形」不再作為驗收依據（D3 的「元件欄改以圖表型別為驗收依據」對其他圖表照舊；這兩列是主控以 D11 明確裁決的例外） |
| G-21 | §9.4 NFR-9.4-02「測試覆蓋率 後端 ≥ 80%、前端 ≥ 70%」 | 前端的覆蓋率只量 `vitest.config.mts` 的 `coverage.include`，整頁視圖由 E2E 驗證、不計入，分支門檻只有 60；QA 報告的前端數字是這個子集的數字，ADR、契約與 Architecture 都沒有登記這個口徑（完整性審查 V-07） | 登記量測口徑（本檔 §4 對應列）；**全量覆蓋率未量**，RTM `NFR-9.4-02` 的證據欄須寫明口徑（QA 合併時處理）；若要以全量範圍量測，另案 |

## 6. 證據欄（待回填；貼逐字輸出，不得寫「應該」）

| 編號 | 項目 | 指令（bash） | 指令（PowerShell） | 逐字輸出（待填） | 回填者 |
|------|------|--------------|---------------------|------------------|--------|
| E-1 | Spring Boot 版本與 3.x 狀態 | `curl -s -H 'Accept: application/vnd.initializr.v2.2+json' https://start.spring.io` | `curl.exe -s -H 'Accept: application/vnd.initializr.v2.2+json' https://start.spring.io` | `bootVersion.default`＝`4.1.1`；`bootVersion.values[].id`＝`4.2.0-SNAPSHOT`、`4.2.0-M2`、`4.1.2-SNAPSHOT`、`4.1.1`、`4.0.9-SNAPSHOT`、`4.0.8`（清單內沒有任何 3.x；W2-A 於 2026-10-14 實測） | W2-A |
| E-2 | Next.js／Tailwind 實際版本 | `npm view next dist-tags --json` | `npm view next dist-tags --json` | `"latest": "16.4.0"`；W3-A 實裝 `next@16.4.0`、`react@19.3.0`、`tailwindcss@4.3.3`（`@tailwindcss/turbopack@4.3.3`）、`typescript@5.9.3`（2026-10-15，`npm ls --depth=0`） | W3-A |
| E-3 | 圖表 spike 結果 | 見 ADR-002 | 見 ADR-002 | 成功：Tremor Raw AreaChart＋recharts 2.15.4 於 Tailwind 4.3.3／React 19.3.0／Next 16.4.0 build＋render 通過（約 5 分鐘）；須 `overrides.react-is`＝19.3.0，否則 Area／YAxis 靜默不渲染（詳見 ADR-002 §D6） | W3-A |
| E-4 | pgvector 映像基底 | `docker run --rm --entrypoint cat pgvector/pgvector:pg18 /etc/os-release` | `docker run --rm --entrypoint cat pgvector/pgvector:pg18 /etc/os-release` | PRETTY_NAME="Debian GNU/Linux 12 (bookworm)"、VERSION_ID="12"（2026-10-15 實跑；PG_VERSION=18.6、PGDATA 預設為 /var/lib/postgresql/18/docker、VOLUME 為 /var/lib/postgresql；apk 不存在，改 apt-get，pgBackRest 2.59.3 支援 PG18） | W2-B |
| E-5 | `internal` 網路上的發布埠可達性 | 見 D14-10 | 見 D14-10 | 只掛 internal 網路的玩具容器：ps 的 Ports 欄為 8080/tcp（沒有發布對應），主機 127.0.0.1:18080 為 Connection refused；加掛非 internal 網路：127.0.0.1:18081->8080/tcp，HTTP 404（連得到）；正式堆疊（只掛 db-net 的 primary／replica）：主機連 5432、5433 皆 Connection refused，5050（pgadmin 另掛 backend-net）、9090、3001 可連（2026-10-15 實跑，詳見 docker/README.md〈9〉#10） | W2-B |

## 7. 後果總評與風險

- **正面**：契約（Architecture §10）與資料所有權（§7）在動工前凍結；偏離逐條可追；平台差異在 W1 就登記。
- **風險**：(1) 對外連線（Initializr、npm、Maven Central、Docker Hub）可能被 auto mode 分類器擋下，W2／W3 需預先放行或由主控代跑骨架生成；(2) Docker daemon 是否在線會變動（W1-A 撰寫初期 `docker ps` 連不上 socket，收尾時 `docker info` 已回 rc=0），每次開工前仍須以 `docker info` rc=0 確認；(3) review／alert 的實作依賴 pause 在步驟邊界精準生效（V-1／V-4），若 W1-B 實證不成立，需開 ADR-003 調整審核閘設計；(4) `gradlew` 索引模式與根層 exec bit 鎖的衝突（D15）須在第一次 commit 前裁決。

---

## 補記（主控 2026-10-15，Bridge／後端／前端／基礎設施交卷後）

### D17　E2E 的 Claude 替身＝`aisdlc-mock-claude`（取代任務書的 dummy_cli 作法）
- **Context**：Bridge 開發者對真引擎實證：`claude.command` 是單一字串、不做 shlex 切分，`PlaybookTask.command` 欄位零消費，`dummy_cli.py` 是讀 stdin 的互動迴圈——「`claude.command` 指到 `python -u dummy_cli.py`」直接 `FileNotFoundError`。
- **Decision**：Bridge 自帶 console script `aisdlc-mock-claude`（POSIX `.venv/bin/`、Windows `.venv\Scripts\*.exe`、映像內在 PATH）；`config_overrides.claude.command="aisdlc-mock-claude"`；旋鈕走請求 `env`（`MOCK_CLAUDE_DELAY`／`TRACE`／`FAIL_REGEX`／`IGNORE_TERM`）。真 Claude 只留給掌舵者手動驗。
- **Consequences**：後端 Phase 4 的整合測試以子行程起 Bridge 並用此替身；Plan D-1 作廢。

### D18　BRD/PRD 解析雙路徑的落地（草案，Phase 3 實作時確認）
- **Decision（草案）**：(a) `executionPath` 下有凍結 SDD 規格 → Bridge `/sdd/compile`；(b) 自由文件 → 後端呼叫 OpenAI 相容 chat completions（PRD §5.2.4 prompt）產三層 JSON，三道有界閘（≤24／Kahn／非空）在後端重現並回結構化 422（US-I-10）；(c) 短句高階目標（貼上文字 < 2,000 字且無標題結構）→ Bridge `/autoclaude/decompose`＋`:approve`。
- **Alternatives**：全部走 GoalDecomposer（只產單層 steps，無法產生多個 Goal）；全部走後端 LLM（違反 PRD §0.4 的引擎映射）。
- **Status**：待 W3-B 實作時確認；見 `docs/04_planning/agent_briefs/W3_BACKEND_P3-6.md`。

### D19　軟刪除保留期與清除排程預設關閉（W5 主控裁決 C-3，2026-10-15；NFR-9.3-04）
- **Context**：PRD NFR-9.3-04 要求「所有刪除操作皆為軟刪除，支援 30 天內復原」。Phase 2 只做了 `is_deleted` 旗標：沒有刪除時間、沒有復原端點、沒有保留期；專案軟刪除還會把 `status` 改成 `ARCHIVED`（附錄 B.1 的終態，手動 API 離不開它）。W4 QA 把 NFR-9.3-04 列為未滿足。
- **Decision**：
  1. **保留期＝30 天**（`console.retention.soft-delete-days`，預設 30）。復原 `POST /api/v1/projects/{id}/restore`（OPERATOR 以上）只在期內可用，逾期回 409 `restore_window_expired`；`GET /api/v1/projects?deleted=true` 列出已刪除的專案（OPERATOR 以上）。
  2. **清除排程預設關閉**（`console.retention.purge-enabled=false`）：實體刪除不可逆，沒有人明確開啟就不會有任何資料被主動刪除；開啟時每日清除逾期的軟刪除專案（連同整棵子資料，以專案為單位一個交易）。保留期與清除是兩件事：期過了、排程沒開 → 資料仍在，只是不能經 API 復原。
  3. **資料面**：Flyway V9 加 `projects.deleted_at`、`projects.status_before_delete`、`goals.deleted_at`、`tasks.deleted_at`；刪除專案時專案與連帶軟刪的目標、任務寫**同一個** `deleted_at`，復原以它辨識「同一次刪除連帶軟刪」的列（刪除專案前就單獨刪除的目標／任務不回來）；復原專案時還原 `status_before_delete`。升級前已軟刪的列以 `updated_at` 近似 `deleted_at`。
- **Alternatives**：預設開啟清除（不可逆，部署者可能不知情就失去資料，否決）；既不提供保留期也永遠不清除（資料無限成長，且違反 NFR-9.3-04，否決）；只提供 DB 手動復原腳本（不是產品功能，否決）；復原一律回 `READY`／`DRAFT`（`COMPLETED`／`FAILED` 專案復原後失去狀態，否決）。
- **Consequences**：`ProjectSummaryResponse` 加 `deletedAt`（只在 `deleted=true` 列表帶值）；契約新增 `project_not_deleted`、`restore_window_expired` 兩個 reason（契約 §0.3 第 5 點、附錄 B.2）；審計新增 `project.restore`／`project.purge`；清除排程的範圍是專案層級，單獨軟刪除的目標／任務不被清除（隨其專案被清除時才一併實體刪除）；預設關閉意味著長期運行的部署必須自行決定是否開啟，並與 pgBackRest 的備份保留期（28 天）一併評估。契約落點：`API_Contract_P3-6.md` §0.5 V9、§1.6；RTM 新列 `API-PRJ-06`。

### D20　等級 6～10 的引擎對映與誠實的能力旗標（W7 主控裁決 D-11，2026-10-16；PRD §5.3.2、§5.5.1.2）
- **Context**：PRD 把「自動突變（Level 6+）」「自演化（Level 7+）」寫成等級 6～10 的能力並各配一個設定鍵；契約 v1.2 因查無對應的引擎鍵標 `UNVERIFIED`，RTM `API-AUT-06` 判 🟡。D-11 授權「真的送引擎」並要求批次回應誠實標示。W7-SA 現查 `AutoClaude/` 的結果（證據表＝契約 §6.6.2，含檔案:行號與原文）：
  1. `minimax.enable_kernel_brain` 為真且有金鑰時，Kernel 在步驟失敗且尚有重試次數時先請 Brain 改寫 prompt；Brain 呼叫失敗則該步驟直接升級。**沒有金鑰而旗標為真，引擎啟動即失敗（`return 1`），不是忽略。** Kernel 呼叫 Brain 時不要求步驟變異，所以實務上只有 prompt 改寫。
  2. `playbook.max_evolutions`、`playbook.require_evolution_signoff` 在生產的 Kernel 路徑**沒有讀者**：Kernel 只發布演化提案並寫日誌，`KernelResult.evolved_playbook_path` 恆為 `None`；`AutoResumeService` 讀 `max_evolutions` 的重載迴圈進不去，也沒有核可閘；`require_evolution_signoff` 只被已沒有建構點的舊 `PlaybookRunner` 讀。引擎自己的測試（`test_proposal_is_logged_but_never_applied`）鎖住「只提案不套用」。
  3. 演化的 AI 提案只由金鑰的有無決定；有金鑰的批次另外會在最後一步之後多一次目標驗證外呼。
- **Decision**：
  1. Console 只送一個引擎旋鈕：`minimax.enable_kernel_brain`＝`model.enableKernelBrain ∨ agent.enableAutoMutation ∨ 自治等級 ≥ 6`，**只在 `model.apiKey` 有值時送**（有金鑰時顯式送 `true`／`false`）。
  2. **永不送** `playbook.max_evolutions`、`playbook.require_evolution_signoff`（另含 `enable_rtm_feedback`、`goal_synthesis_enabled`、`enable_translation_auto_propose`，對 Console 的 playbook 沒有可觀測效果或會關掉既有檢查）。
  3. `agent.enableAutoMutation` 的 effect 由 `UNVERIFIED` 改 `ENGINE`；`agent.enableSelfEvolution` 由 `UNVERIFIED` 改 `STORED_ONLY`（已驗證不影響引擎）。
  4. 批次回應與 `execution_runs.engine_capabilities`（Flyway V10）回報 `{autoMutation, selfEvolution}`，值域 `ENABLED`／`OFF`／`UNAVAILABLE_NO_API_KEY`；`selfEvolution` 有金鑰即 `ENABLED`（引擎沒有開關），語意是「只提案、不套用」。
- **偏離 PRD**：PRD §5.3.2 說 6～10 級「含自動突變、自演化」；引擎現況只有 Brain 逐步校正、自演化只提案（登記於 §4）。
- **Alternatives**：照主控預設方案送 `max_evolutions`／`require_evolution_signoff`（否決：兩鍵無讀者，標 `ENGINE` 為假；`require_evolution_signoff=true` 製造假的 fail-closed 安全感——`AutoResumeService` 缺核可閘，日後若 Kernel 產生 `evolved_playbook_path` 這個鍵也保護不了任何事；QA 只能驗到無作用的鍵）；金鑰按需遞送讓 `selfEvolution=OFF` 成真（否決：改變「有金鑰就送」的既有行為，目標驗證會悄悄停止，D-58 的 E2E 關閉演化手法也要重寫）；沒有金鑰時仍送 `enable_kernel_brain=true`（否決：引擎啟動即失敗）。
- **Consequences**：Console 的「自演化」開關沒有引擎效果，UI 以 `STORED_ONLY` 標籤與 tooltip 如實呈現；日後若 AutoClaude 讓 Kernel 真的套用演化，須先在 `AutoResumeService` 補核可閘，再由新 ADR 決定 Console 是否送這兩個鍵；Docker 全棧的 Bridge 環境本身必填金鑰，`engineCapabilities` 只認 Console 的 `model.apiKey`，方向是低估；`resume`／`restore` 沿用建立時凍結的設定檔，金鑰在批次中途被清掉會讓重新啟動失敗。契約落點：`API_Contract_P3-6.md` §0.5 V10、§1.2.1、§3.4.2、§3.6.1、附錄 C、E2E-14、§6.6；Architecture §6(c)、§7、§11.4、§12.1 L-10／L-11；RTM `API-AUT-06` 由 QA 依證據升級。

### D21　資源使用情況的資料來源（W7 主控裁決 D-12，2026-10-16；US-M-10）
- **Context**：G-18 與契約 v1.2 把「資源使用情況（CPU／記憶體）」標為 Bridge 沒有資料來源（RTM `US-M-10` 🟡）。
- **Decision**：Bridge 在背景每 5 秒以 psutil 對每個存活 run 的**引擎行程樹**取樣（CPU 整機正規化、RSS 總和、行程數、取樣時間），`GET /autoclaude/runs/{id}` 的回應加 `resources`（只增不減）；console-api 把它投影到 `ExecutionRunDetailResponse.bridge.resources`；前端 Agent 即時狀態卡顯示 `CPU 12.3%・記憶體 345 MB・3 行程`，沒有資料顯示 `—`。資源**不入庫、不進 SSE**。
- **Alternatives**：在請求路徑現場取樣（阻塞請求，且 `cpu_percent(interval=None)` 第一筆恆為 0）；寫進 `execution_runs`（違反 D10 的欄位所有權分工，資料高頻且沒有追溯價值）；走 SSE `metric-update`（多一條事件契約與重播語意，現有 15 秒詳情輪詢已足夠）。
- **Consequences**：PAUSED 時 Bridge 已終止行程樹（D8），`resources` 為 null；樣本超過 15 秒未更新回 null，不回舊數字；畫面數字最舊約 20 秒；取樣器必須跨 tick 持有 `psutil.Process` 物件，否則 CPU 恆為 0.0。契約落點：§1.2.3、§3.1.2、§4.3 M-19、E2E-14 第 8～9 列；Architecture §10.1。

### D22　AISDLC_SDD 的接入、深度探針與三項偏離（W7 主控裁決 D-16、D-17，2026-10-16；PRD §0.2、§0.3、§0.4、NFR-OBS-01）
- **Context**：PRD 把 FSM-STATE 列為 Console 對 SDD 的遙測來源（§0.3：Run＝FSM-STATE session、監控遙測＝FSM `decision_trace`／`retry_history`／RTM）；Bridge 早有 `GET /sdd/version`、`GET /sdd/fsm/{project}`，但 Console 後端與前端沒有任何消費者，NFR-OBS-01 的「四源一致」也從未比對 FSM-STATE（完整性審查 I-01、I-02、V-06）。另外，Console 的探測環打淺層 `/health`（恆 ok），引擎或 `SDD_ROOT` 壞了也看不出來（I-03）。W7-SA 現讀 AISDLC_SDD v0.30 的真實 FSM 狀態檔：`retry_history` 是**以重試閘為鍵的映射**、`human_pending_tracking` 是**單一映射**、**沒有任何 RTM 覆蓋數值的鍵**（證據：契約 §6.7.2 E1～E3）。
- **Decision**：
  1. **唯讀接入**：Bridge 新增 `GET /sdd/fsm`（FSM 專案清單），`GET /sdd/fsm/{project}` 增 `human_pending`、`retry_history`、`rtm_coverage`（只增不減；語意以上述真實結構為準，契約 §3.1.3）；console-api 新增 `GET /api/v1/engines/sdd`（Bridge 不可達也回 200，以 `available`／`reason` 表達）；監控頁新增「AISDLC_SDD 引擎」卡（版本、FSM 專案選單、當前狀態／Sprint／更新時間、待人工、最近 5 筆決策；30 秒輪詢）。
  2. **深度探針（D-17）**：`autoclaude.healthCheckPath` 預設改 `/health/deep`（Flyway V11 只改仍等於舊預設的既有列）；Bridge 的 `/health/deep` 加 `sdd` 檢查：沒有可用 SDD 目錄為 `null`、有目錄且（有 `build/reports/fsm` **或**入口文件 `AISDLC_SDD_INIT.md`）為 `true`、否則 `false`——**`sdd` 只當資訊：`ok:false` 不觸發 503，`/health/deep` 的 200／503 只由 `git`／`autoclaude`／`workspace`／`db` 四項決定，頂層 `reason` 不含 `sdd`**（主控裁決 Q1、Q4）。**與主控任務書字面不同**：任務書寫「無 `build/reports/fsm` 即 false、整體 503」，但 `AISDLC_SDD/.gitignore` 忽略 `AISDLC_SDD_v0.30/build/reports/`（入庫 0 筆），乾淨 clone 沒有 fsm 目錄，照字面判會讓 compose 的 `engine-bridge` 永遠 unhealthy、`backend` 起不來；而 SDD 是選用引擎，它壞了不該被當成 Bridge 不可用（INFRA 實測發現並已偏離，主控裁決採之；契約 §3.1.1、§6.7.3 Q1／Q4）。
  3. **三項偏離 PRD**（逐項登記於 §4）：①**FSM 不走 SSE、改 30 秒輪詢**——FSM 檔只在 SDD runtime 執行時才變動（人工操作頻率），Bridge 事件型別只有六種且沒有 FSM 事件，要推送就得讓 Bridge 監看檔案，成本高、收益低；②**decompose 以 AutoClaude `GoalDecomposer` 為唯一分解器，SDD 規格走路徑 A 編譯**——不另建「呼叫 SDD skill」的分解路徑；③**signoff 與 `HUMAN_PENDING` 只做語意對映，Console 只讀、不回寫 FSM-STATE**——回寫會繞過 SDD FSM runtime 的不變量，AISDLC_SDD Rule 9 把「繞過 `FSMRuntime` 直接讀寫 `FSM-STATE-*.yaml`」列為違反即停機的禁令；Console 只顯示 `humanPending`，不替 SDD 簽核。
- **Alternatives**：FSM 走 SSE（否決：見上）；Console 回寫 FSM-STATE（否決：Rule 9）；RTM 覆蓋率由 Bridge 另讀 RTM 檔（否決：超出本輪；FSM-STATE 沒有該鍵，`rtm_coverage` 先為保留位，現況恆 null，列為後續候選）；`/health/deep` 對 `sdd` 照字面判（否決：乾淨 clone 全棧起不來）；`sdd` 失敗觸發 503（否決，主控裁決 Q4：SDD 是選用引擎，503 會讓 Agent 可用率下降並誤報 `AGENT_UNRESPONSIVE`；改為只當資訊）。
- **Consequences**：`GET /engines/sdd` 在乾淨 clone 回 `available=true`、`projects=[]`（正常狀態）；開發機上會列出 SDD 測試套件留下的 `FSM-STATE-test-<數字>.yaml`（照列，斷言一律寫「包含」）；探測環只對 `git`／`autoclaude`／`workspace`／`db` 四項自檢敏感，`sdd` 無效只顯示在 Console 的 SDD 卡；探測讀取逾時 3→8 秒；`human_pending.count` 實務上只有 0 或 1；Bridge 與 SSOT 對 SDD LATEST 的判定可能分歧（Architecture §12.2 V-11）；Console 對 FSM 的唯一消費點是 `GET /engines/sdd`。契約落點：§1.7.1、§3.1、§3.1.1、§3.1.3、§4.3 M-20、附錄 B.4、E2E-15、E2E-16 第 1～2 列；Architecture §4.3、§10、§10.1、§11.1、§11.2；RTM 新列 `API-ENG-01`、補強 `NFR-OBS-01`。

### D23　refresh token 撤銷名單的設計（W7 主控裁決 D-19，2026-10-16；D16 的落地）
- **Context**：見 D16（原決定三項全未實作）。W7-SA 現查：JWT 已為每個 token 簽發 `jti`（`JwtTokenService.build` 的 `.id(UUID)`）；後端只有 `login`、`refresh` 兩個認證端點，前端 `logout()` 只清 sessionStorage；後端沒有 Redis 相依。
- **Decision**：①鍵＝refresh token 的 `jti`，存活到 `exp`；②**換新時原子撤銷舊 token**（`tryRevoke`：Redis `SET NX EX`／記憶體 `putIfAbsent`；回 false＝已撤銷＝401 `INVALID_REFRESH_TOKEN`）；③新增**免認證**的 `POST /api/v1/auth/logout`（`{refreshToken}`，請求格式合法一律 204，不洩漏 token 有效性），前端 `logout()` 先 fire-and-forget 呼叫、失敗不阻擋本機登出；④Redis 優先、不在線降級為單實例記憶體名單並記 WARN（只在狀態轉換時記）；⑤`console.security.refresh-revocation.store`＝`auto`（預設：`spring.data.redis.host` 有值才用 Redis）／`redis`／`memory`；⑥`management.health.redis.enabled=false`。
- **Alternatives**：只做換新輪替、不加 logout 端點（否決，主控裁決 Q6 視同核可 logout 端點：否則登出後被竊的 refresh token 仍可用到過期，最長 7 天）；撤銷名單存 PostgreSQL（可行，但 D16 的 Redis 已配置）；同時撤銷 access token（否決：每個請求都要查名單，違背 JWT 無狀態的簡單性；access 最長 30 分鐘）；換新給「重放寬限窗」（否決：讓被竊的 token 在窗內可重放，且多一份狀態）。
- **Consequences**：①降級記憶體名單隨行程重啟清空，重啟前已登出、尚未過期的 refresh token 在重啟後復活（Redis 在線時不會）；②換新回應在網路上遺失時，舊 token 重試得 401 而被登出（機率很低，不做寬限）；③access token 在登出後最長 30 分鐘仍有效；④後端新增相依（契約附錄 D.4）；⑤多實例部署前須改成只認 Redis（記憶體名單只對單一實例有效）；⑥`POST /auth/logout` 是主控給定的新路徑清單之外的第三條（主控裁決 Q6 視同核可，契約 §6.7.3）。契約落點：§1.9、§2.8 第 10 點、§0.4 第 7 點、附錄 D.2／D.4、E2E-16 第 7～10 列；Architecture §8.1；RTM 新列 `API-AUTH-03`。

### 主控親驗紀錄（2026-10-15）
- Bridge：`ruff` 全過；`pytest -n 4` 235 passed／9 skipped（無 DB）；slim 映像字面指令 build rc=0、容器 `/health` 兩引擎 ok。
- 後端：`sh gradlew clean build` Test result SUCCESS（448 支）、Checkstyle、JaCoCo 驗證、BUILD SUCCESSFUL。
- 前端：lint 0／tsc 0／build 成功（20 路由）／vitest 104 案例／Playwright 對真後端＋PG 17 passed／版面唯一性 grep 為空。
- 基礎設施：compose config 四 profile rc=0；14 支 .sh shellcheck／bash -n／CR 零問題；`--profile db up --wait` rc=0 全 healthy、串流複製 streaming async 且副本讀到主庫寫入、`pgbackrest check` WAL 歸檔 repo1＋repo2（MinIO）、全備兩 repo 成功、`down -v` 清場。
