# 任務書 W1-A：Architect ＋ SA（規劃與架構文件；不寫產品程式碼）

> 先讀 `COMMON_CONTEXT.md`（同目錄）。本任務書只講你的範圍。

## 你的角色
你是 AgentConsole 的首席架構師兼系統分析師。你的產出是**後續所有開發 agent 的地圖**：目錄結構、服務拓樸、資料流、契約、需求追溯矩陣（RTM）。文件要精準、可機械核對，不要散文。

## 必讀（按順序）
1. PRD 全文 `docs/01_requirements/Agent_ConsoleUI_PRD.md`（3,576 行，請真的讀完；§0 凌駕後文）。
2. UI 設計 README `docs/01_requirements/01.UI_Design/Design_ConsoleUI/README.md`。
3. `AutoClaude/CLAUDE.md`（只需〈專案架構〉〈模型欄位〉〈CLI〉三節）＋ `AutoClaude/autoclaude/models/playbook.py`（PlaybookTask 欄位）＋ `AutoClaude/autoclaude/execution/goal_decomposer.py`（decompose／approve 介面）。
4. `docs/04_planning/AutoSDD_Capability_Integration_Map.md`（ConsoleUI 在整體願景中的位置）。
5. 兩個既有子專案的 `CLAUDE.md` 開頭 60 行（學它們的子專案指引體例）。

## 交付物（全部放 `AgentConsole/`，繁體中文）
### 1. `AgentConsole/docs/02_architecture/Architecture.md`
必含章節（用這些標題）：
- §1 系統脈絡（C4 L1，ASCII 圖）：掌舵者 → Console → Engine Bridge → AutoClaude／AISDLC_SDD；共用 PostgreSQL 18。
- §2 容器圖（C4 L2）：11 個服務（nginx／frontend／backend／engine-bridge／postgres-primary／postgres-replica／redis／pgadmin／pgbackrest／prometheus／grafana）＋ 埠號表 ＋ 三個網路（frontend-net／backend-net／db-net internal）＋ volumes。數值一律取自 PRD §11。
- §3 目錄地圖：**逐字採用**下方〈目錄地圖（已拍板）〉，可補充子目錄但不可改頂層。每個目錄一句話說它放什麼。
- §4 後端 Clean Architecture 分層（PRD §4.1 套件樹）＋ 依賴方向規則（adapter→application→domain；infrastructure 只被 application port 反向注入）。
- §5 前端結構：App Router 路由樹（PRD §4.2）＋ **四區塊共用版面**：`Top`（公告列＋主導覽列，對應設計稿 Topbar+Masthead）／`Tools`（左側導航＋我的專案 rail）／`Content`（路由內容）／`Bottom`（底部列）。明文：三個共用區塊各只有一個元件檔，改一處全站生效。
- §6 資料流四條（序列圖或編號步驟）：(a) CRUD；(b) BRD/PRD 匯入 → Bridge `/autoclaude/decompose` → 草案 signed_off=false → signoff → 落 Goal/Task；(c) 執行：後端 signoff 二次校驗 → 建 execution_runs → Bridge `POST /autoclaude/runs` → spawn → SSE 轉發到前端；(d) 監控：後端從 execution_steps／runs 聚合。
- §7 `execution_runs` 寫入分工表（COMMON_CONTEXT 已拍板，照抄成表）。
- §8 安全：JWT／RBAC（Admin／Operator／Viewer 各能做什麼，列表）、NFR-SEC-03 消毒鏈、SEC-04 外呼 allowlist、SEC-05 token_guard 群組校驗。
- §9 執行模式：「本機開發」（只起 PG 容器，三個服務本機跑，埠 3000／8080／8081）與「Docker 全棧」（compose 11 服務）兩種，各一段啟動步驟。
- §10 Bridge API 契約：**逐字採用**下方〈Engine Bridge API 契約（已拍板）〉。
- §11 後端 API：引用 PRD §7 為 SSOT，不重抄端點表；但補一張 **DTO 欄位表**（Project／Goal／Task／ImportRecord／ExecutionRun／SystemConfig 的 Request／Response 欄位，camelCase，取自 PRD §5／§6）。

### 2. `AgentConsole/docs/02_architecture/ADR-001-TechStack-Lock.md`
ADR 體例（Context／Decision／Alternatives／Consequences）。至少涵蓋：Spring Boot 4.1.x（3.x EOL 證據＝start.spring.io metadata 現查）、Next.js 16 + Tailwind 4、圖表 Tremor Raw 先 spike／shadcn chart 備援、JWT 最小認證、Flyway 擁有 DDL、Bridge 自有 venv、Docker build context 取 monorepo 根（Bridge 映像需 COPY AutoClaude/）、pause 語意、mock E2E 策略。偏離 PRD 之處逐條標「偏離 PRD §x，理由」。

### 3. `AgentConsole/docs/06_quality/RTM.md`（需求追溯矩陣，最重要的交付物）
一張總表，**逐條列出** PRD 內所有可驗證需求，一列一項，不准合併：
- 使用者故事：US-P-01～06、US-G-01～07、US-T-01～06、US-I-01～10、US-E-01～11、US-M-01～10、US-S-01～08。
- API 端點：§7.1.1～§7.1.8 每一列（含 signoff 四條、token-guard、SSE 兩條）。
- Bridge 端點：§10 契約每一條。
- NFR：§0.5 六條、§9.1～9.4 每一列。
- 部署：§11.2 每個服務；§12 的 streaming replication／WAL 歸檔／pgBackRest 全備／差備／pg_dump 離站／verify 演練／手動 failover／Prometheus 指標／Grafana 面板。
- UI：九個畫面（設計稿 README 的 1～9）＋ 四區塊共用版面 ＋ Markdown 編輯器八項功能（PRD §5.1.4）。
欄位：`ID | 來源 | 摘要（≤20 字）| 層（FE/BE/Bridge/Infra）| Phase（PRD §10 的 1～6）| 實作檔 | 自動測試 | E2E 驗證 | 狀態`。狀態初值一律 `⬜ 未開始`；其餘填「待填」。表尾附統計列（各層各 Phase 的列數）。這張表之後由每位開發 agent 回填、由 QA 核對。

### 4. `AgentConsole/docs/04_planning/Implementation_Plan.md`
PRD §10 六個 Phase → 本輪派工波次對照（W1 架構＋Bridge；W2 後端 P1+P2＋Infra；W3 前端 P1+P2＋後端 P3～6；W4 前端 P3～6＋QA；W5 修復）。每波列入口條件、出口閘門（**可執行指令**＋預期輸出字樣）。留「進度帳」小節給主控填。

### 5. `AgentConsole/CLAUDE.md`（≤ 200 行）
體例仿 `AutoClaude/CLAUDE.md`：繁中規範、目錄地圖、三個服務各自的開發指令（install／run／test／lint）、Docker 一鍵、閘門清單、鐵律（抄 COMMON_CONTEXT 的〈鐵律〉）、文件索引。指令要寫**絕對路徑或相對於 `AgentConsole/`** 並註明。

### 6. `AgentConsole/README.md`（≤ 80 行）
快速開始：前置需求、本機開發三步、Docker 全棧三步、看到什麼算成功。

### 7. 建立空目錄骨架
`AgentConsole/{frontend,backend,engine-bridge,docker}` 各放一個 `README.md`（3～5 行，說這裡要放什麼、誰負責、入口檔在哪）。**不要**生成任何框架程式碼（Next／Gradle／FastAPI 骨架由各開發 agent 自己生成，避免互踩）。

## 目錄地圖（已拍板，逐字採用）
```
AgentConsole/
├── CLAUDE.md / README.md / docker-compose.yml / docker-compose.dev.yml / .env.example
├── docs/{02_architecture,04_planning,06_quality}/
├── frontend/            Next.js 16（app/ components/{layout,ui,charts,markdown,domain} lib/ styles/ tests/ Dockerfile）
├── backend/             Spring Boot 4.1 / Java 21（src/main/java/com/aisdlc/console/{adapter,application,domain,infrastructure}；src/main/resources/db/migration/V1__init.sql；Dockerfile）
├── engine-bridge/       FastAPI（app/{main.py,settings.py,runner.py,events.py,locks.py,db.py,security.py,routers/{autoclaude.py,sdd.py}} tests/ pyproject.toml Dockerfile .venv/）
└── docker/{nginx,postgres/{primary,replica},pgbackrest,redis,prometheus,grafana}/
```

## Engine Bridge API 契約（已拍板，逐字採用；Bridge 開發者同時在實作它）
```
GET  /health → {"status":"ok","bridge_instance":"<id>","engines":{"autoclaude":{"ok":true,"version":"…"},"sdd":{"ok":true,"latest":"AISDLC_SDD_v0.30"}}}
POST /autoclaude/runs
  body {"run_id":"<uuid=console execution_runs.id>","project":"…","execution_path":"<abs>",
        "playbook":{version,project,global_goal,global_invariants,tasks[{step_id,name,prompt,command?,expected_output_regex?,evaluator_command?,max_retries?,goal_task_id?}]},
        "config_overrides":{…AutoClaude config.yaml 子集…},"env":{…},"fresh":false}
  → 201 {"run_id","status":"RUNNING","pid","workspace","bridge_instance"}
  → 409 {"code":409,"reason":"advisory_lock_held","holder_run_id"}   → 422 {"code":422,"reason":"…","violations":[…]}
POST /autoclaude/runs/{run_id}:pause  → 202 {"status":"PAUSING"}（下一步驟邊界轉 PAUSED）
POST /autoclaude/runs/{run_id}:resume → 202 {"status":"RUNNING"}
POST /autoclaude/runs/{run_id}:stop   → 202 {"status":"CANCELLING"}（SIGTERM→30s→SIGKILL→CANCELLED）
GET  /autoclaude/runs/{run_id} → {"run_id","status","pid","started_at","completed_at","exit_code","current_step","completed_steps","total_steps","tokens_used","last_event_seq"}
GET  /autoclaude/runs/{run_id}/stream?after=<seq>   SSE（亦認 Last-Event-ID）
     每則 `id:<seq>` `event:<log|status|step|token|review-request|alert>` `data:<json>`
     log {seq,ts,level,line}；status {seq,ts,status,reason}；step {seq,ts,step_id,step_number,status:STARTED|COMPLETED|FAILED|RETRYING,attempt}；token {seq,ts,pct,tokens_used}
GET  /autoclaude/runs/{run_id}/events?after=<seq>&limit=<n> → REST 重播（SSE 斷線回補基礎）
GET  /autoclaude/runs/{run_id}/checkpoints → [{"checkpoint_id","name","created_at","step_idx","step_id","is_automatic"}]
POST /autoclaude/runs/{run_id}/restore  body {"checkpoint_id"} → 202
POST /autoclaude/decompose  body {"goal","context","project","max_steps"≤24,"config_overrides"}
  → 200 {"draft_id","goal_hash","reasoning","playbook":{…},"signed_off":false}
  → 422 {"code":422,"gate":"max_steps|cycle|empty_prompt|brain_unsupported|brain_failed","detail"}
POST /autoclaude/decompose/{draft_id}:approve body {"approver":"<非空>"} → {"signed_off":true,"approver","approved_at","playbook"}；approver 空→400
GET  /sdd/version → {"latest":"AISDLC_SDD_v0.30","root":"<abs>"}
GET  /sdd/fsm/{project} → FSM-STATE-{project}.yaml 內容（current_state、decision_trace 尾 5 筆）或 404
POST /sdd/compile body {"spec_dir":"<abs>"} → {"tasks":[…PlaybookTask…],"scenario","contracts"} 或 422（spec 未凍結／格式）
```
Bridge 執行狀態：INITIALIZING／RUNNING／PAUSING／PAUSED／CANCELLING／COMPLETED／FAILED／CANCELLED；**寫進 PG `execution_runs.status` 時只用 PRD 六態**（PAUSING→RUNNING、CANCELLING→RUNNING）。

## 驗收（你自己跑，交卷貼輸出）
- `find AgentConsole -type f | sort`（列出你建立的每個檔）。
- `wc -l AgentConsole/CLAUDE.md`（≤ 200）。
- RTM 列數：`grep -c '^| US-\|^| API-\|^| BR-\|^| NFR-\|^| INF-\|^| UI-' AgentConsole/docs/06_quality/RTM.md`（ID 前綴自訂但要一致，並在表頭說明），且對照 PRD 使用者故事總數 58（P6+G7+T6+I10+E11+M10+S8）一條不漏——在交卷列出你數到的各類列數。
- 全文無簡體／英文段落（專有名詞除外）。
