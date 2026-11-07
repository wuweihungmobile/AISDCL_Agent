輸入快照：HEAD＝01d9be6e；主控裁決 D-01～D-66

# ADR-003：ResearchToPRD 在 AgentConsole 的載體、持久化、流程脊與相依（Research-to-PRD）

| 項目 | 內容 |
|------|------|
| 狀態 | **定稿候選 v1.0.0-rc3**（SCG-0 獨立審查後由主控依〈凍結常態規則〉凍結；凍結後變更須新增 ADR-00N 並引用本檔） |
| 建立日期 | 2026-11-02 |
| 決策者 | 掌舵者授權主控代決（主控裁決 D-12～D-66，附錄 C.2、C.7 見 PRD）；Architect 提案、SD 合成 |
| 適用範圍 | `AgentConsole/`（frontend、console-api、engine-bridge）及其對 AutoClaude run、AISDLC_SDD FSM CLI 的呼叫面；不含框架側方法層（那是框架 ADR-001） |
| 上位文件 | [ADR-001](ADR-001-TechStack-Lock.md)（D4 SSE、D17 mock claude、D22 FSM 唯讀投影）、[ADR-002](ADR-002-Frontend-Design-System.md)、根層 `docs/04_planning/ADR/ADR-XPLAT-016-sdd-integration-loop-minimal-intrusion.md`、`docs/04_planning/ADR/ADR-XPLAT-017-bridge-fsm-write-surface.md`、PRD `docs/01_requirements/ResearchToPRD_PRD.md` |
| 相關文件 | [API_Contract_ResearchToPRD.md](API_Contract_ResearchToPRD.md)、[Architecture.md](Architecture.md)（§2.2／§3／§5.1／§5.4／§6／§7／§8／§9.4／§10／§11／§12 的本輪增補）、`AgentConsole/docs/04_planning/ResearchToPRD_Plan.md` |

---

## 1. Context

掌舵者 2026-11-02 要求把「研究議題→證據→PRD→四方審查→Gate 0→分流→內環落地→交付」做成 Console 內單一有狀態工作流，並要求研發全程入庫、納入 AISDLC_SDD 流程。本 ADR 記錄 AgentConsole 側的載體與持久化決定。FSM 兩把鍵與 Bridge 動詞白名單的決定在 ADR-XPLAT-017（跨專案）；框架側方法層在框架 ADR-001。每則決策寫**決策／替代案／WHY／再開症狀**；再開症狀一律是可觀測事件，不用日曆或計數（同 SOP S7）。

## 2. 決策總表

| 編號 | 決定 | 偏離？ |
|------|------|--------|
| D1 | Phase 0 的執行載體＝AutoClaude stage run 鏈＋Bridge 確定性 orchestrator（(b′)） | 修正主控預決 D-04 的「傾向單一 playbook run」 |
| D2 | 研究表由 fail-loud 寫入器＋檔案 outbox 寫入；無 `BRIDGE_DB_DSN` 一律 503（能力探針除外），不降級 | 不沿用既有 best-effort `BridgeDb`（`db.py:12-13`） |
| D3 | 檔案與 DB 的真相關係＝三類流向；`state.json` 非權威 | 補充 ADR-001 D22 |
| D4 | Bridge 是研究表唯一寫入者；console-api 零寫入 | 無 |
| D5 | 流程脊＝DB 游標（外環）＋純函式衍生（內環）；單一路由 `/research/[researchId]`＋`?step=`；無 `steps:advance` | 偏離來源 §6.1 的五個並列入口與五頁 |
| D6 | 事件帳 `research_events`＋SSE 重播 | 補充 ADR-001 D4 |
| D7 | 研究抓取＝Bridge 原生（API 層）＋headless Web（產業層）；Web 層預設關；清單獨立、釘 IP、ADMIN 管理 | 補上 Architecture §8.4 誠實劃界承認缺的「解析後驗 IP」 |
| D8 | 工作區預設 repo 外；軌道 B 複製驗證、原處保留，不搬動 | 偏離來源 §2 的「根目錄」字面；偏離 SA-08 的「複製後改名」 |
| D9 | 新前端相依 `mermaid`（strict、動態載入）與 `diff` | 偏離 ADR-002 D7 的相依集合（新增二者） |
| D10 | Docker 全棧只跑 mock claude 的 E2E；真研究限本機模式 | 無 |
| D11 | ESCALATION 沿既有恢復指令呈現，不新增恢復動詞；另有「換世代」鈕（放棄舊鍵，非恢復；僅 ADMIN；D-60、D-64） | 無 |
| D12 | 不動 Top／Bottom 共用區塊；只做 `ResearchFlowHeader` | 偏離來源 §6.1 的全域頂列 |
| D13 | 兩把 FSM 鍵（外環 `research-<slug>`、內環 `<sub>-<slug>`）；細節在 ADR-XPLAT-017 | 修正主控預決 D-01 的單鍵 |
| D14 | 軌道 B 範本採登記制（`scaffold_templates/<name>/`）；P1 只交 `python-fastapi` | 無 |
| D15 | 發佈機制：tag＝`git tag -a`、PR＝`git push -u origin`＋`gh pr create`（本機模式）；不由伺服器執行 OS 開啟指令 | 無 |
| D16 | Bridge 子行程白名單：git／gh 一律 argv 陣列、`shell=False`、經 `procutil` helper | 無 |

## 3. 逐項決策

### D1　Phase 0 的執行載體＝AutoClaude stage run 鏈＋Bridge 確定性 orchestrator（(b′)）
- **決策**：以 AutoClaude run 當執行載體（重用行程樹管理、SSE、checkpoint、Token Guard、advisory lock），形態是**一串短 stage run**：`RESEARCH`（Web 層啟用時含 WebSearch／WebFetch）→`DRAFT`（`spec-engineer`）→`REVIEW-k`（4 步＝4 角，各步 `maintain_context:false`）→（FAIL）`REVISE-k`→`REVIEW-k+1`…；P1 另有 `TCS_DRAFT`。確定性部分（解析輸出、驗 schema、聚合評分、寫 DB、呼 FSM）全在 Bridge 的 orchestrator 碼，不由 LLM 決定；審查輪列只在輪有結果時（前置否決已判，或四維審查卡皆通過驗證並彙整、`gate` 已回傳）與分數列、缺陷列、事件同一交易一次寫入，進行中、取消、中斷、輸出無效只記在 `REVIEW-k` stage run 與事件，不寫輪列、不佔 `round_no`、不耗預算（D-55、D-57）。每步 `maintain_context:false`、步驟間只經檔案交接；prompt-by-reference（Bridge 編譯期讀框架 agent YAML，轉成工作區 `.prompts/<role>.md` 並記 sha256 入 `research_stage_runs.prompt_manifest`，步驟 prompt 只寫「先 Read 該檔再執行」）；研究 run **不進** `execution_runs`／`execution_steps`，另記 `research_stage_runs`／`research_events`；`BRIDGE_RESEARCH_MAX_CONCURRENT_RUNS=1`；請求 `env` 帶 `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`（與步驟牆鐘同源）、步驟 prompt 禁止背景任務與子代理。
- **實作期訂正（2026-11-03；見文末〈勘誤記錄〉第 2 列）**：(1) run 級工具集改為 `Read`、`Glob`、`Grep` 加 `Edit(//<工作區絕對路徑>/**)`（審查 run 只放行該輪 `02_governance/reviews/round-<k>/**`；路徑為小寫磁碟機字母、無冒號、正斜線、`//` 起頭）——真機（claude 2.1.316、Windows、headless、acceptEdits）量測 `Write(<任何寫法>)` 一律被拒、只有此 `Edit` 形態建得出檔，裸 `Write` 能寫工作區以外而不給（D-74）；Web 工具只在該專案產業層為真且 Web allowlist 非空時給研究 run；(2) 步驟逾時預設 600 秒＝引擎 Kernel 路徑固定的步驟逾時（原 1200 秒大於引擎上限，看門狗永遠不會先響；真需求再讓引擎 Kernel 路徑讀 `config.playbook.step_timeout_seconds`，列 P1 候選；D-75）；(3) 並行上限 1 時第二個 stage 一律 409 `stage_conflict`（`details.cause=max_concurrent_runs`），不排隊（D-67）；(4) 研究 stage run 一律釘關引擎 Brain（`minimax.enable_kernel_brain` 為 false）且子行程環境不傳 `MINIMAX_*`，失敗路徑走規則引擎、零外呼（D-79）。
- **替代案**：(a) Bridge 自己 spawn `claude -p`；(b) 單一大 playbook；(c) 讓 LLM 自己決定迴圈與停止。
- **WHY**：(a) 重寫 `runner.py` 的行程樹、孤兒回收、SSE、checkpoint；(b) 工具集是 run 級（`AutoClaude/autoclaude/utils/config.py:148`）、`PlaybookTaskIn` 無 per-step 工具欄（`engine-bridge/app/models.py:46-61`）、「≤3 輪審查」跨 run 且靜態 playbook 無資料驅動停止、研究 run 不該進 `execution_steps`（`db.py:100-114`；`execution_steps.task_id NOT NULL REFERENCES tasks`，`V1__init.sql:113-125`）；(c) 違反 12-Rule Rule 5（能由碼回答的就由碼）與有界停機。`maintain_context` 預設 True，會以 `--continue` 接上同 cwd 最近的對話——可能是上一位審查者（`models.py:57`、`pty_executor.py:73-74`），故每步 false。DEF-200-575（`claude -p` 背景等待上限）只作用於主回合結束後仍有背景任務者（`tools/lib/unattended_authz.py:40-44,57-61`），步驟不含 Task／Agent 工具、prompt 禁背景任務，故不觸發；仍加請求 env 作第二道。
- **再開症狀**：AutoClaude 日後支援 per-step `allowedTools` 且能資料驅動停止；或 stage 間交接（工作區檔案）出現一次因上一 run 殘留造成的誤判。

### D2　研究表 fail-loud 寫入＋檔案 outbox；無 DSN 不降級
- **決策**：研究表（V16～V19）由 Bridge 的 `ResearchDb`（fail-loud）寫入。持久化協定＝寫檔（原子 replace，重用 `fsutil.write_text_atomic`）→ outbox 記錄 → DB 交易（資料列＋`research_events`＋`last_event_seq`）→ 標 done；DB 不可用＝stage run `BLOCKED_DB`＋`research.alert`、退避重試；重啟重放 outbox（自然鍵 UNIQUE 保冪等）。**審查結果的寫入順序與崩潰窗口（D-58(b)）**：Bridge 在呼叫 `gate` **之前**先把輪結果（聚合分數、四維分數、缺陷、`prd_version_no`、`trigger_kind`）落到 outbox；`gate` 回傳後補 `fsm_gate_result`／`fsm_retry_count`／`verdict`，並在同一交易寫輪列、分數、缺陷、事件；重放 outbox 時先以 FSM `show` 讀 `decision_trace`／`retry_history` 判斷該輪的 `gate` 是否已呼叫（已呼叫＝只補 DB、不重呼叫；未呼叫＝先呼叫再寫），使 `gate` 呼叫與輪列寫入對崩潰冪等（`gate` 已呼叫而 DB 未寫是 D-57 必然留下的窗口）。**例外（D-59(5)）**：POST_HUMAN 通過輪依設計不呼叫 `gate`（D-50），重放時不得套「未呼叫就補呼叫」（否則在 HUMAN_PENDING 送出非法的 `gate PASS`），該輪只補 DB。`BRIDGE_DB_DSN` 未設時**所有研究端點一律 503 `research_requires_db`**（唯一例外：能力探針 `GET /research/capabilities` 仍回 200 並標 `db:false`，讓 UI 能顯示停用原因；D-49），不降級成純檔案模式。寫入端點須 `X-Bridge-Token`＝`BRIDGE_RESEARCH_WRITE_TOKEN`（另立；規則同 `BRIDGE_SI_WRITE_TOKEN`：未設 503 `research_write_disabled`、缺或錯 403 `research_write_forbidden`、佔位字串或短於 32 字元＝啟動即 `SettingsError`）。
- **替代案**：沿用 `BridgeDb` best-effort（`db.py:12-13`）；`BRIDGE_DB_DSN` 缺時退回純檔案。
- **WHY**：D-11「研發全程入庫」是硬需求；best-effort 會讓「畫面有、DB 沒有」靜默發生；純檔案模式下 Console 的時間軸與斷點本來就是空的（`AgentConsole/CLAUDE.md` 環境變數表），研究流程不能建在它上面。
- **再開症狀**：outbox 重放出現一次重複或遺漏事件；或使用者因 `BLOCKED_DB` 橫幅頻繁中斷而要求降級模式。

### D3　檔案與 DB 的真相關係：三類流向，`state.json` 非權威
- **決策**：agent／人作者的檔案（`evidence_items.json`、PRD、審查 JSON、TCS）＝**檔→驗→DB**（檔案內容為憑證）；Bridge 作者的檔案（`evidence_matrix.md`、`review_card.json`、`route_decision.json`、`issue_scope.json`）＝**DB→渲染→檔**；`state.json`＝匯出、**不得被讀回**。FSM 真相＝`FSM-STATE-*.yaml`（只經 `FSMRuntime`，Rule 9 禁令 1）；流程游標真相＝`research_projects`。對帳（`:reconcile`）只報告不修復，結果追加 `research_events`（`research.reconcile`）。`evidence_items.json`、審查者單維度 JSON、`review_card.json` 與 `issue_scope.json` 的契約 SSOT＝框架 `docs_template/sdd/requirements/` 的四份模板（Bridge 以 `<!-- r2p:contract=… -->` 標記對拍，D-43）；審查算法為整數式 `W100`，顯示值兩位小數、不四捨五入（D-42）。資料庫以三種觸發器鎖住不可變與單向轉移：append-only 守衛、通用受控可更新守衛（表名→允許更新欄位清單）、缺陷 `status` 與來源 `verification` 的專用單向守衛（D-49）。
- **替代案**：DB-only（失去 SDD digest 與 git 憑證）；file-only（失去查詢、重播、Diff）。
- **WHY**：凍結 digest 與 git 需要檔案；Console 需要可查詢與可重播。
- **再開症狀**：`:reconcile` 報出任何一筆檔案↔DB 漂移，或 `state.json` 被發現被某程式當輸入。

### D4　Bridge 是研究表唯一寫入者；console-api 零寫入
- **決策**：Bridge 是 `console.research_*` 唯一寫入者；console-api 以 JDBC（`JdbcClient`，無 JPA 實體）讀；ArchUnit 加一條「`adapter.out.persistence.research..` 不得出現 `INSERT|UPDATE|DELETE`」的字串掃描測試。人工決定的內容（`approver` 取 JWT subject 由 console-api 轉傳）寫 `research_gate_decisions`，「誰對哪個實體做了請求」由 V6 `audit_log`（`AuditLoggingFilter`）記，兩者以 `audit_trace_id`＝`trace_id` 互證。
- **替代案**：console-api 寫人工決定表（它擁有 `projects`、`signoff`）。
- **WHY**：沿 Architecture §7 的「每表一個寫入者」；Gate 0 的結果（digest、FSM 態）只有 Bridge 知道，兩邊都寫＝雙寫競態。
- **再開症狀**：Bridge 不可用時使用者無法留下決定（需 console 側 outbox）；或 ArchUnit 字串掃描被繞過。

### D5　流程脊：DB 游標（外環）＋純函式衍生（內環）；單一路由＋`?step=`；無 `steps:advance`
- **決策**：游標欄位 `research_projects.flow_step／flow_phase／flow_status／flow_detail`，**只由 Bridge 在引擎動作同一交易寫入**並附 `research.step` 事件；步驟 3 以後的相態（`BUILDING`／`HEALING`／`AWAITING_HUMAN`／`PAUSED`／`RELEASE_PENDING`／`DELIVERED`）是 `execution_runs` 與內環 FSM 的函數，由 console-api 純函式 `ResearchFlowPolicy.effective(research, project, latestRun, fsmView)` 衍生，不落 DB。路由只有兩條：`/research`（清單）與 `/research/[researchId]`（工作區，`?step=topic｜studio｜route｜build｜deliver`）；`?step=` 超前於 `furthestStep` 導回游標所在步。導覽登記表加 1 列 `{id:"research", label:"研發工作流", href:"/research", mobile:false, enabled:true}`（D-13）。**沒有 `steps:advance` 端點**。
- **實作期訂正（2026-11-03；見〈勘誤記錄〉第 5 列）**：`flow_status` 的衍生優先序為 `ESCALATED`＞`RUNNING`＞`FAILED`＞`WAITING_HUMAN`＞`IDLE`：stage run 失敗、取消或被回收時，呼叫端以 `last_run_failed` 明說、游標寫 `FAILED`＋`flow_detail`＝`exit_reason`（取消為 `cancelled`），`flow_phase` 回到 stage 開始前的可重入相態（D-77）；不帶 `generation` 的 `reinit` 在 `flow_status=FAILED` 時一律可呼叫（初始化失敗補建；stage 失敗或取消只清標記並依 FSM 現態重衍生；D-81）。
- **實作期訂正（2026-11-07；見〈勘誤記錄〉第 6 列）**：Bridge `:route` 為**同步**呼叫（D-105）：成功 200、失敗 502 `route_step_failed`，牆鐘 `BRIDGE_ROUTE_TIMEOUT_SECONDS`＝300 s，console-api 對 `route` 與 `decomposition` 的 Bridge 讀取逾時 330 s（nginx `/api/` 既有 `proxy_read_timeout 86400s`，不改）；游標執行中 `route／ROUTING／RUNNING`、成功 `build／ROUTED／IDLE`、失敗 `route／ROUTING／FAILED`＋`flow_detail=<failure_step>`；TCS 凍結後的游標以「讀端衍生＋`:reconcile` 校正＋SDD freeze 後觸發」三段處理（D-125），BLOCKED_DB 後於 outbox 重放的同一交易重新衍生（D-128）。
- **替代案**：每步一條路由（五頁，說明鎖要五條、導覽測試面變大）；全部衍生無游標（離開再回來無法定位 Gate 前的相態）；Bridge 為內環 run 掛 hook 寫游標（侵入 `RunManager`）；console-api 提供 `steps:advance` 並自寫游標（違反 D4）。
- **WHY**：`HELP_ROUTES` 路由鎖以 `app/**/page.tsx` 為準（`lib/help/registry.ts:4`）；來源規格自己的動機＝「避免頁面跳轉破碎」；內環相態是 `execution_runs`／FSM 的函數，衍生最不易漂移；`mobile` 必須 false——`registry.test.ts:107,143` 數的是 `NAV_REGISTRY.filter(e=>e.mobile)` 全列（含停用的 `import`），現況已 6 列＝上限（實查 `lib/nav/registry.ts:42-115`）。
- **再開症狀**：`ResearchFlowPolicy` 的衍生結果與實際 FSM／run 狀態矛盾一次；或 `?step=` 深連結在 Next 路由器下出現無法返回的歷史堆疊。

### D6　事件帳＋SSE 重播（`research_events`）
- **決策**：`research_events(research_id, seq)` append-only，每專案單調 `seq`＝SSE `id`；`GET /api/v1/stream/research/{id}` 認 `Last-Event-ID`、每 15 s `heartbeat`，斷線先 REST `GET …/events?afterSeq=` 回補再接串流；**重播不完整**（緩衝已逾期或有序號缺口）時伺服器先送 `research.replay_gap`（`fromSeq`、`toSeq`），客戶端收到該事件或偵測到 `id` 不連續即全量重抓（專案詳情、列表、`afterSeq` 事件）再重新訂閱（D-49）；事件型別見 API 契約 §3；`research.review` 只在輪完成時送（含 verdict），進行中的審查聽 `research.run`（D-57）。
- **替代案**：純輪詢；借用 `execution` 事件。
- **WHY**：研究步驟（抓取、審查）不是 `execution_steps`；每專案單調 `seq` 讓 `Last-Event-ID` 與 REST 回補同構（Architecture §5.3；ADR-001 D4）。
- **再開症狀**：多實例 Bridge（單行程配號假設不成立，L-R9）。

### D7　研究抓取：Bridge 原生（API 層）＋headless Web（產業層）；Web 層預設關；清單獨立、釘 IP、ADMIN 管理
- **決策**：學術／開源／Stack Exchange 走 Bridge httpx（取得真位元組＋sha256＋`research_fetches`，查證層級可達 V3：V3 取 arXiv HTML 版頁面，無 HTML 版者維持 V2，不取 PDF）；產業層走 headless `WebSearch`／`WebFetch`（≤V2，`observed_by=AGENT_DECLARED`），`BRIDGE_RESEARCH_WEB_ALLOWLIST` 預設空＝Web 層關閉。抓取清單為**研究專屬獨立清單**，檢查函式為包裝 `check_research_url`（D-62(3)：先呼叫既有 `check_outbound_url` 取 parser 一致性，再加 https 限定、埠 443 限定、尾點拒絕、解析後私網 IP 拒絕；不修改 `check_outbound_url`——它接受 http、任意埠與尾點，`security.py:275-303`）；Bridge 補上「解析後驗 IP＋釘連線」：resolve→拒 `127/8、10/8、172.16/12、192.168/16、169.254/16、::1、fe80::/10、fc00::/7`→以解析後 IP 連線並設 `Host`／SNI→`follow_redirects=false`、逐跳重驗→逐筆寫 `research_fetches`（含被拒者，`outcome=DENIED_*`；解析不出 host 的被拒外呼仍入庫：host 寫保留字 `(unparsed)`〔非空、不是合法主機名，D-61 的 host 非空 `CHECK` 放行〕、url 取原字串前 500 字元、`outcome=DENIED_ALLOWLIST`、`http_status` NULL；D-66）；回應體上限 5 MiB、逾時 20 s。**初始清單＝arXiv（`export.arxiv.org`、`arxiv.org`）、Semantic Scholar（`api.semanticscholar.org`）、GitHub API（`api.github.com`）、Stack Exchange API（`api.stackexchange.com`）**（D-17）；產業部落格網域由 ADMIN 逐一加入（表 `research_allowlist_entries`、端點 `POST／PATCH /api/v1/research/allowlist` 僅 ADMIN）；Reddit 預設不在任何清單，加入須 `tos_acknowledged`；有效清單＝環境變數基底 ∪ 啟用中的 ADMIN 條目，每個 stage run 的有效清單快照入 `allowlist_snapshot`。各來源速率限制：主控已現查 arXiv、GitHub（含搜尋端點）、Semantic Scholar 的官方數值並回填 PRD NFR-R2P-03-6（Bridge 內建下限表；一律另遵守伺服器回傳的限流訊號）；Stack Exchange 原因官方頁無法抓取而未現查，已於 2026-11-03 由 V-R9（PKG-BR-B）以直接 GET 官方頁落證並回填，3 秒維持為保守取值（D-40）。
- **替代案**：全部走 headless Web；全部 Bridge 原生；擴大 `BRIDGE_OUTBOUND_ALLOWLIST`（模型端點清單）；僅部署環境變數管理 allowlist（Architect 草稿）；原樣重用 `check_outbound_url`（否決：它接受 http、任意埠與尾點，與 NFR-R2P-03-1 的嚴格判準不符；改動它又會動到既有 `test_security` 對模型端點清單的語意）。
- **WHY**：引擎 `web_search` 是 no-op stub（`tool_invocation_adapter.py:5-11`）；API 抓取有真位元組與授權欄；擴大模型端點清單違反最小權限（誤設的 `minimax.base_url` 可指向研究主機）；Bridge 自己是 HTTP 客戶端，故能補 Architecture §8.4 誠實劃界承認缺的 IP 釘住；D-17 要求「ADMIN 逐一加入」，僅環境變數無法由 ADMIN 在產品內操作。headless Web 層 Bridge 觀測不到單筆呼叫，只認 agent 宣告（L-R1），故降為 ≤V2。
- **再開症狀**：審查發現 agent 宣告的來源不可開或內容不符（偽造）一次；或 `WebFetch(domain:…)` 規則無法機械約束（V-R1 失敗）；或 V-R4 實測 httpx 釘 IP＋SNI 不可行（退回「解析後比對 IP 非私網」並登記）。

### D8　工作區預設 repo 外；軌道 B 複製驗證、原處保留，不搬動
- **決策**：`BRIDGE_RESEARCH_ROOT` 預設 **repo 外**：Windows `%USERPROFILE%\.autosdd\my-project\`、POSIX `~/.autosdd/my-project/`、Docker `/workspace/my-project`；可覆寫，必須在 `BRIDGE_ALLOWED_PATH_ROOTS` 之下（`BRIDGE_RESEARCH_ROOT` 與 `BRIDGE_SCAFFOLD_ROOT` 自動併入允許根），啟動時驗證並於 `GET /health/deep` 的 `research.root` 揭露；根 `.gitignore` 仍加 `/my-project/`（防手動設到 repo 根下時入庫）。V-R2 改為負向驗證：確認工作區不載入根 `CLAUDE.md` 鏈與根 hooks。軌道 B「搬入」＝複製→逐檔 sha256 驗證→**原工作區原地保留**（不改名、不刪除）；本功能**不新增** `os.replace`／`rename`／`move` 站點（原子寫檔重用 `fsutil.write_text_atomic`）。
- **實作期訂正（2026-11-07；見〈勘誤記錄〉第 7 列）**：①軌道 A 的 worktree 根 `BRIDGE_WORKTREE_ROOT` 預設 `<BRIDGE_RESEARCH_ROOT>/_worktrees`（併入允許根），以 `git -c core.longpaths=true worktree add -b <feature/…> <path> <base_ref>` 建立（`-c` 為逐次行程選項，不寫任何 config 檔；D-95）；②軌道 B 的副本**含** `00_research/raw/**`（逐檔 sha256 驗證），以範本 `.gitignore` 的 `00_research/raw/` 排除入版控（D-117）。
- **替代案**：預設 `<monorepo>/my-project/`（D-03 原案；P0 加 token 量測閘）；軌道 B 用 `move`；軌道 B 複製後把舊目錄改名為 `.moved-*`（SA-08 原案）。
- **WHY**：工作區在 monorepo 內會讓每個 `claude -p` 步驟載入根 `CLAUDE.md` 鏈與根 hooks（BRIDGE §8.6:541；額度守衛會擋 WebFetch／WebSearch 扇出），既費 token 又干擾研究；使用者層無 `CLAUDE.md` 與 hooks（主控實查），repo 外是乾淨執行面；`~/.autosdd/` 已是本系統持久目錄慣例（`tools/lib/endurance_env.py`）。Windows 改動目錄項的原語會踩檔案鎖（根 `CLAUDE.md` 鐵律三〈Windows 檔案鎖〉列），新增站點須動根層 `TestDirEntryPrimitivesAreAccountedFor`（`tools/tests`，開發棒不得碰、屬收尾單人窗口）；改名不增加安全性，保留原處更簡單且可回復（「修復不留後遺症」）。偏離來源 §2「根目錄 `my-project/`」字面，WHY 如上。
- **再開症狀**：V-R2 負向驗證失敗（repo 外工作區仍載入了根 `CLAUDE.md` 鏈）；或軌道 B 複製後舊工作區殘留造成混淆。

### D9　新前端相依：`mermaid`（動態載入、`securityLevel:'strict'`）、`diff`
- **決策**：新增 `mermaid` 與 `diff` 兩個相依（D-39）：Mermaid 只在 client、`next/dynamic` 延遲載入、`securityLevel:'strict'`、渲染逾時 3 s、失敗顯示原始碼；Diff 為行級函式庫（無 DOM），PRD 預覽沿既有線性 prism（`components/markdown/rehypePrismLinear.ts`）避開逐行 O(n²) 的 20 KB 根因；雷達圖用既有 `recharts` 的 `RadarChart`。bundle 增量與 200 KB 量測已於 2026-11-03 回寫於下方〈量測〉。
- **量測（2026-11-03 回寫；量測機 Intel Core i5-14600K／20 邏輯核／127.7 GB／Windows 10.0.26300／Chromium 156.0.8078.4／production standalone／viewport 1440x900；見〈勘誤記錄〉第 1 列）**：
  - **相依**：`mermaid` 12.2.0（MIT）、`diff` 8.0.4（BSD-3-Clause；原為 shadcn 的間接相依、自帶型別，所以不加 `@types/diff`）；`dependencies` 只多這兩鍵；`npm ci` rc 0（1053 packages）；`npm audit` 29（1 low／22 moderate／6 high）與改前相同。
  - **bundle**（路由 `/research/[researchId]` 首次載入 JS，raw／gzip 位元組）：改前基準（頁殼無面板）13 檔 840,806／273,134；PKG-FE-C 完成時 16 檔 1,298,679／411,193（+54%；首屏中 Markdown 管線單一 chunk 325,892／94,160）；PKG-FE-D 把預覽管線改在 `StudioPanel` 內以 `next/dynamic` 載入後 15 檔 972,234／316,614（對基準 +15.6%／+15.9%，在「+20% 內」預算〔raw 1,008,967／gzip 327,761〕之內；對 FE-C 完成時 −25.1%／−23.0%）；`/research` 清單路由 878,493／284,955（改前 853,617／276,402）。`mermaid` 約 18 個 chunk（合計 1,444,505／325,379）無一在首屏；`diff` 為獨立 1 個 chunk（8,316／3,143）、不在首屏（Diff 分頁才 import）。
  - **200 KB PRD**（`gen_prd_200kb.py` 固定種子 20261102；v2 恰 204,800 bytes、3,313 行、預覽 345 區塊；AT-960-17-1）：輸入延遲 P95（3 輪×50 鍵）20.7／13.5／11.9 ms（門檻 100；跨 6 次執行範圍 11.9～23.3 ms）；Diff 計算 5 次中位 1 ms、最大 2 ms（門檻 1000）；預覽首次渲染 5 次中位 90.4 ms、最大 119.2 ms（門檻 2000；FE-D 動態載入後冷啟動約 366.7 ms＝第一次下載 326 KB 管線的代價）；預覽全部畫完中位 402.2 ms；DOM 5,745 節點。
  - **決策與實證**：`RICH_EDIT_MAX_BYTES`＝30 KB（原暫定 40 KB）——編輯器套件輸入延遲 P95 近似線性（10 KB 26～30、20 KB 36～45、30 KB 57～63、40 KB 72～77、60 KB 103～120 ms，超過 100），超過即改用精簡 textarea（200 KB 純文字輸入 12～23 ms）；Diff 組合＝`diff` 套件為主（`maxEditLength` 取 `DIFF_MAX_EDITS`），超界（回傳 undefined）退回 PKG-FE-A 的自寫 `diffLines`（`data-diff-engine` 標 library 或 fallback）；Mermaid 設 `htmlLabels:false` 並加強輸出淨化（`strict` 只淨化腳本與事件屬性、仍留 `<img src>`，且函式庫量測版面時把標籤 HTML 放進真文件，瀏覽器在淨化前就對外發請求；修後零外呼）；預覽不顯示 `<!-- r2p:section=N -->` 整行錨點（編輯器套件的選用屬性，不傳＝行為不變）；雷達圖刻度軸 90°→45°。
  - **劃界**：頁殼（Server Component）改 `next/dynamic` 載入 `StudioPanel` 無效（client reference 仍隨路由預載，首次載入反而 1,299,186），所以改在 client 元件內動態載入預覽區塊；首次載入（manifest 指標）與其他步驟省約 326 KB，但編輯器套件模式下的工作室步（`?step=studio`）實際網路量不變——編輯器自己的 chunk 群組共用同一個 Markdown chunk，掛上後非同步載入、不在首屏路徑。
- **替代案**：只顯示 Mermaid 原始碼；伺服器端渲染；自寫行級 diff。
- **WHY**：來源規格要求即時渲染與 Diff 模式；`package.json:20-48` 無此二者（Grep）；strict＋逾時＋失敗回退原始碼控制 XSS 與體積。
- **再開症狀**：`mermaid` 出現安全公告；或首屏／路由 bundle 超 P0 TCS 量測定下的預算（路由 `/research/[researchId]` 首次載入 JS 對改前基準 +20% 內，數字見上〈量測〉）。

### D10　Docker 全棧：能力探針＋mock claude E2E；真研究限本機模式
- **決策**：Docker 全棧只跑 mock claude（`aisdlc-mock-claude`）的 E2E；真研究與軌道 A／B 的 git／GitHub 副作用限**本機模式**（Bridge 在主機）；Bridge 映像不裝 `claude`／`gh`；`GET /health/deep` 揭露 `research.mode`（`local`／`mock-only`）與能力探針（`claude_cli`、`gh_cli`、`git`、`scaffold_root`…，資訊欄、不使深度探針整體失敗）；`mock-only` 時 UI 停用「啟動深研」並說明。
- **實作期訂正（2026-11-03；見〈勘誤記錄〉第 3 列）**：`mock-only` 或劇本模式（`MOCK_CLAUDE_RESEARCH_SCRIPT` 有設）時，研究 stage 的預取一律不連網，改讀劇本 JSON 頂層選填鍵 `prefetch` 指向的夾具（經與真抓取相同的入庫路徑；紀錄 `outcome=OK`、`fetch_method=API`、`observed_by=BRIDGE`——DDL 的 `outcome` 列舉沒有 `MOCK`，不新增值），無夾具＝`no_evidence` 但不外呼；真抓取只在本機模式（D-78）。切換劇本後 Bridge 容器須 `up -d --force-recreate` 並以 `docker exec … echo $MOCK_CLAUDE_RESEARCH_SCRIPT` 驗證容器內的值（TCS AT-960-22-2 跑法註記）。
- **替代案**：Bridge 映像安裝 `claude`＋`gh`。
- **WHY**：映像刻意不含 `claude`（`Dockerfile:5-8`）、無 `gh`（`:22-30`）、compose 允許根只有 `/workspace`（`docker-compose.yml:230`）；容器內放 OAuth 憑證是姿態變更；既有 E2E 體例就是 mock claude（ADR-001 D17）。
- **再開症狀**：掌舵者要求「容器內真研究」。

### D11　ESCALATION 沿既有恢復指令呈現，不新增恢復動詞
- **決策**：重用 `SddEscalationBlock` 顯示恢復指令＋兩顆按鈕（D-60）：「我已恢復，繼續（僅一次機會）」——只讓 Bridge **唯讀**驗 FSM 現態已離開 ESCALATION*（否則 409 `fsm_state_conflict`）才續跑，不呼叫任何 FSM 寫入動詞（引擎不歸零計數：恢復後至多再得一次審查，PASS 歸零、FAIL 立即再 ESCALATION）；「換世代」——放棄這一把外環鍵並另開新世代鍵 `research-<slug>-g<N+1>` 取得全新預算（框架工作流第 2.5 節既有路徑；舊鍵留 ESCALATION、不恢復），須填理由並二次確認，**僅 ADMIN**（D-64：`reinit` 在 `SecurityConfig` 為通用 OPERATOR 規則、matcher 無法依請求本文分流，所以角色檢查分兩段：VIEWER 由既有授權鏈擋下〔403 `ACCESS_DENIED`〕，OPERATOR 通過授權鏈後由 `ResearchCommandService` 在服務層擋下〔403 `research_write_forbidden`〕，兩者 Bridge 請求數 0），經 `reinit` 的 `generation:"next"` 模式、記 `research_gate_decisions(ABANDON_KEY)`；`resume-from-escalation` 不入 Bridge 白名單；不做無理由、無確認的「換鍵重開」單鍵（大型 SCR＝新研究專案帶 `parent_research_id` 已涵蓋）。
- **替代案**：Console 提供 `resume-from-escalation` 按鈕；自動恢復；無理由、無確認的「換鍵重開」單鍵（D-60 改為受確認的「換世代」鈕）。
- **WHY**：R-9.5／絕對禁令 6；BRIDGE §6.8:260-262；`SddEscalationBlock` 已有 UI（`components/domain/sdd/SddEscalationBlock.tsx:17`）；「換世代」是放棄舊鍵、不是恢復，不增第二條恢復路徑；引擎的 `resume-from-escalation` 不動 retry 計數（`state_loader.py:211-269,271-274`），把這個真實語意寫進規格比留給實作期猜安全（D-60）。
- **再開症狀**：使用者回報終端恢復步驟是流程主要卡點。

### D12　不動 Top／Bottom 共用區塊；研究工作區自帶 `ResearchFlowHeader`
- **決策**：狀態燈（Idle／Running／Healing／Paused／Escalated）、Token 速率與預算只做在 `ResearchFlowHeader`（研究工作流內元件）；不動 `TopRegion`／`BottomRegion`／`ToolsRegion`；全站狀態燈列為延後項。
- **替代案**：Top 加 Scope Selector／AutoClaude 狀態燈／Token 儀表板（來源 §6.1）。
- **WHY**：現有 Top 只有 Bridge 狀態點（`TopRegion.tsx:20,37,63-64`），Bottom「不得放任何新功能」（Architecture §5.2:366）；改共用區塊＝全站測試面，且有四份凍結 TCS 釘住。
- **再開症狀**：掌舵者在研究工作流之外要求看到研究 run 狀態。

### D13　兩把 FSM 鍵（細節見 ADR-XPLAT-017）
- **決策**：外環鍵 `research-<slug>`（狀態目錄在研究工作區 `build/reports/fsm`，Bridge 唯一建檔點）；內環鍵 `<sub>-<slug>`（分流後建於目標專案標準狀態目錄，Stage-1 採納含已發佈的 PRD）；兩鍵以 DB（`research_projects.fsm_project`、`research_route_decisions.impl_fsm_project`）與 `--reason` 互指。
- **替代案**：單鍵。
- **WHY**：單鍵與「工作區目標無關」互斥：adapter 以「向上找含 `build/reports/fsm` 的目錄」定位狀態檔，軌道 A 的 TCS 必須住目標 `docs/03_testing/contracts/`，spec_dir 的祖先裡找不到工作區的狀態目錄 ⇒ 內環整條斷（BRIDGE §8.11:593-596；ADR-XPLAT-016 §3.5:172）。
- **再開症狀**：見 ADR-XPLAT-017 D1。

### D14　軌道 B 範本採登記制（`scaffold_templates/<name>/`）；P1 只交 `python-fastapi`
- **決策**：範本清單取自 Bridge `app/research/scaffold_templates/<name>/` 目錄（`GET /research/capabilities` 回 `scaffold_templates[]`）；P1 只交 `python-fastapi`（GitHub Actions、`docker-compose.yml`、`.env.example`〔僅 `<YOUR_…>`〕、可跑的最小 pytest／AT 綁定）；展開為確定性模板代換（不用 LLM；變數只准 `[A-Za-z0-9_-]`，輸出路徑 `resolve()` 後須在新根之下）；node／java 以症狀再開。
- **實作期訂正（2026-11-07；見〈勘誤記錄〉第 8 列）**：`BRIDGE_SCAFFOLD_ROOT` **無預設**（未設＝軌道 B 停用，由 `capabilities.scaffoldRoot` 與預演缺項 `scaffold_root` 揭露）；新增 `BRIDGE_REPO_ROOT` 覆寫（未設＝現行 `REPO_ROOT`，`repo_writable()` 改讀它）；範本內 Python 檔一律以 `.tmpl` 後綴存放、展開時去後綴（避免被 AST 鎖解析；D-96、⚖P1-18）。
- **替代案**：一次做 python／node／java 三棧；範本放框架側。
- **WHY**：只有 python 能走既有 AT 綁定與 evaluator（evaluator 只收 `pytest`，BRIDGE §7:312-313）；一次做三棧沒有凍結綁內容可驗；範本是 Bridge 的確定性展開資產，不是框架方法層。
- **再開症狀**：掌舵者要求某個非 Python 技術棧。

### D15　發佈機制：tag＝`git tag -a`、PR＝`git push`＋`gh pr create`（本機模式）；不由伺服器執行 OS 開啟指令
- **決策**：Release Tag 由 Bridge 以 argv 陣列執行 `git tag -a <tag> -m <msg>`（tag 名 `^v[0-9]+\.[0-9]+\.[0-9]+(-[a-z0-9.]+)?$`；前置 FSM＝RELEASE_READY 與 RTM 100%；遠端存在且 ADMIN 已確認才推送；已存在回 409 `tag_exists`）；建立 PR 由 Bridge 執行 `git push -u origin <branch>`（不帶 `--force`）與 `gh pr create --base <base_ref> --head <branch> --title … --body-file …`（標題與內文由 PRD 與追溯表摘要確定性產生，ADMIN 於確認框預覽）；GitHub token 由 console-api 取自 `system_configs` 加密欄（設定鍵 `research.github_token`，**由 Flyway V20 只種一列設定、不加表；D-98 原「不加 DDL」訂正為「不加表、只種一列設定」，D-132**）、於單次請求本文傳給 Bridge，只進子行程 `GH_TOKEN` env，不入 argv／檔案／log／DB。「開啟本地專案」只顯示並複製路徑＋前端 `vscode://file/<path>` 連結，**不由伺服器啟動 GUI**；「檢視 PR」只開符合 `^https://github\.com/[^/]+/[^/]+/pull/[0-9]+$` 的 URL。
- **替代案**：以 GitHub REST API（Bridge httpx，`api.github.com` 已在抓取 allowlist）建 PR——否決：與軌道 B 的 `gh repo create` 同為本機模式依賴，Docker 模式本就只跑 mock（D10），容器無 `gh` 不構成選 REST 的理由；Bridge 以 shell 啟 GUI 開啟本地專案——否決：任意執行面。
- **WHY**：D-16 把機制交 Architect 裁定而草稿未涵蓋，SD 依上述事實裁定；`gh` 與 `git` 皆由 `gitops` 單一模組以白名單呼叫（D16）。
- **再開症狀**：掌舵者要求在 Docker 模式也能建 PR（改採 REST）；或 `gh pr create` 在 Bridge 環境下的認證行為出現一次非預期（V-R8）。

### D16　Bridge 子行程白名單（git／gh）
- **決策**：`app/research/gitops.py` 是 `git`／`gh` 子行程的唯一出口：argv 陣列、`shell=False`、環境以白名單重建（移除 `BRIDGE_*`、`SDD_*`、`PYTHONPATH`；另設 `GIT_AUTHOR_*`、`GIT_COMMITTER_*`、`GIT_TERMINAL_PROMPT=0`、`GCM_INTERACTIVE=never`、`GIT_OPTIONAL_LOCKS=0`；D-99、D-128 F-13）、逐次選項 `-c core.longpaths=true`（D-95）、一律經 `procutil.popen_platform_kwargs()`（Windows 帶 `CREATE_NO_WINDOW`，避免 OpenConsole 洩漏）。**允許集合**：`git`：`status --porcelain`、`rev-parse`、`diff --name-only`、`ls-files`、`worktree add -b <feature/…> <path> <base_ref>`、`init -b main`、`add -A`（僅新專案根內）、`add -- <明列路徑…>`（軌道 A；逐路徑 `check_path`、須在 worktree 內，軌道 A 仍禁 `add -A`；D-99）、`worktree list --porcelain`、`commit -m`（訊息取自模板、不含使用者原文；作者以 `GIT_AUTHOR_*` 環境設定）、`remote add origin <url>`、`push -u origin <branch>`、`tag -a`；`gh`：`auth status`、`repo create <owner>/<name> --private|--public --source . --push`、`pr create`、`release create`（選用）。**禁止形態**：`--force`／`-f` 類強推與強制、`reset --hard|--merge|--keep`、`clean`、`stash`（含裸 `stash`）、`checkout -- <path>`、`restore <path>`、`switch -f`、全域或系統層 `git config`、任何寫入 `~` 的設定；使用者可影響的 argv 片段先過列舉或正規式（分支名 `^feature/[a-z0-9-]{1,40}$`、庫名 `^[a-z][a-z0-9-]{1,38}$`、可見性二值）。能力登記測試：`gitops` 外不得出現 `git`／`gh` 子行程。
- **替代案**：沿用 `AutoClaude` 的 evaluator 白名單；在 console-api 呼叫。
- **WHY**：根 `CLAUDE.md` 鐵律五（毀滅性 git 形態已由 PreToolUse 阻斷，Bridge 的程式內路徑同樣不得產生這些形態）；判準必須精準（擋到無法工作的守衛會被關掉）：只列舉本功能需要的動詞。
- **再開症狀**：白名單測試發現本功能需要的動詞不在清單內（須先改本 ADR 再改碼）；或 V-R8 顯示 `gh` 在 Bridge 環境下的認證路徑需要新的動詞。

## 4. 誠實劃界（已知限制；進 Architecture §12）

| ID | 內容 | 處置／再開症狀 |
|----|------|---------------|
| L-R1 | headless WebSearch／WebFetch 的逐筆呼叫 Bridge 觀測不到，只認 agent 在 `evidence_items.json` 宣告（`observed_by=AGENT_DECLARED`，≤V2） | 審查發現宣告的 URL 不可開／內容不符→降級該來源並記缺陷 |
| L-R2 | 審查獨立性（R-9.20.3 型）在 AutoClaude 路徑結構上不成立：同一 AI、同工作區可互讀（BRIDGE §6.4:211-213） | 補償：分 run、`maintain_context:false`、聚合由碼、Gate 0 人工；**不宣稱滿足** |
| L-R3 | Docker 全棧無 `claude`／`gh`、無 repo 可寫 bind：真研究與軌道 A／B 的 git／GitHub 只在本機模式 | `capabilities` 探針＋UI 停用說明（D10） |
| L-R4 | 工作區位置：預設 repo 外（D8）；若部署者把 `BRIDGE_RESEARCH_ROOT` 設到 monorepo 下，每個 `claude -p` 會載入根 `CLAUDE.md` 鏈（token 成本）與根 hooks | V-R2 負向驗證；根 `.gitignore` 仍加 `/my-project/` |
| L-R5 | `transition`／`gate` 為舊 CLI 契約（非單行 JSON） | Bridge 預檢＋事後驗證；再開症狀：誤判一次→框架 CLI 加 `--json` |
| L-R6 | 非 Python 標的無 AT 綁定（evaluator 只收 `pytest`，BRIDGE §7） | P1 只做 `python-fastapi`（D14） |
| L-R7 | 狀態檔 load-modify-save 無跨行程鎖（BRIDGE §6.10:301） | 外環鍵只由 Bridge 單行程寫；人在 SDD session 手動並寫＝已知競態 |
| L-R8 | 軌道 B `gh repo create` 需操作者本機 `gh` 已登入或請求帶 token | `capabilities.gh_cli`（V-R8） |
| L-R9 | `research_events` 與 `research_projects.last_event_seq` 配號在單一 Bridge 行程下安全；多實例 Bridge 需改用序列或 advisory lock | 現行單 worker（`Dockerfile:57`）；再開症狀：Bridge 水平擴展 |
| L-R10 | Stack Exchange 速率限制官方數值原先未現查（官方頁無法抓取）；2026-11-03 V-R9 已以直接 GET 官方頁現查並回填 PRD NFR-R2P-03-6（arXiv、GitHub、Semantic Scholar 先前已現查） | 3 秒為保守取值（不是官方數字）＋遵守伺服器回傳限流訊號；V-R9 已結 |
| L-R11 | 框架對 HUMAN_PENDING 的 72 小時提醒／168 小時升級只由 hooks SessionStart 執行；Console 路徑沒有 hooks（D-48(3)） | P0 以 UI 顯示等待時長＋滿 72 小時橫幅提醒，不轉 REMINDER、不自動升級；再開症狀：掌舵者回報因 Gate 0 久未核准而錯過提醒 |

## 5. 待實測（零信任：下列為「本文標為未驗證」的點，各棒落證據；歸屬見計畫書）

| ID | 點 | 驗法（PowerShell 形態） |
|----|----|------------------------|
| V-R1 | headless `claude -p` 的 `--allowedTools "WebFetch(domain:…)"` 語法與無提示行為 | 暫存目錄 `claude -p --permission-mode acceptEdits --permission-prompts none --allowedTools … "<一句提示>"`，看 rc 與輸出（2026-11-03 結案：真機結論見 D1 實作期訂正與 D-74——`Write(<任何寫法>)` 一律被拒，只有 `Edit(//<小寫磁碟機無冒號路徑>/**)` 建得出檔） |
| V-R2 | 負向：repo 外工作區是否不載入根 `CLAUDE.md` 鏈與根 hooks、每回合 token | 同一提示分別在 repo 外工作區與 repo 內 `my-project/x` 各跑一次，比 `--output-format json` 的 usage 與 `--debug hooks` |
| V-R3 | Windows `-p <prompt>` 命令列長度與 `.prompts/` 參照法 | 構造 20 KB／40 KB 提示對比 |
| V-R4 | httpx 釘 IP＋SNI 的可行性 | 單元測試對本機假伺服器 |
| V-R5 | 無 `MINIMAX_API_KEY` 時 evaluator 失敗後的重試行為 | mock claude＋失敗 evaluator 觀察 `engine-N.log` |
| V-R6 | 新狀態目錄首次 `show`（不帶 `--must-exist`）建檔行為與第 3 次 FAIL 後現態 | 暫存 `SDD_STATE_DIR` 下實跑（腳本見計畫書附錄） |
| V-R7 | `spec-frozen --stage Gate-0 --digest --root <工作區>` 的相對 `--doc` 與摘要 | 同上 |
| V-R8 | Bridge 環境下 `gh auth status`／`GH_TOKEN` 行為 | 本機模式 |
| V-R9 | Stack Exchange 官方速率限制（其餘三來源主控已現查並回填 NFR-R2P-03-6） | 以官方頁 `https://api.stackexchange.com/docs/throttle` 現查，回填 NFR-R2P-03-6 與 allowlist 條目（2026-11-03 結案：WebFetch 對該站回「unable to fetch」，改以 PowerShell `Invoke-WebRequest` 直接 GET，HTTP 200，已回填；3 秒仍為保守取值） |

## 6. 連動面（同一個 commit 收齊，不留尾巴）

`Architecture.md` 的 §2.2／§3／§5.1／§5.4／§6(e)／§7／§8／§9.4／§10／§11.1／§11.3／§12 增補；`API_Contract_ResearchToPRD.md`；Console PRD §0.9 與 §8.1 導覽註；每期 `RTM-ResearchToPRD-P<N>-<日期>.md` 子表與 `RTM.md` 存根；根 `.gitignore` 加 `/my-project/`、`agentconsole-ci.yml` 的 `paths`、`docker-compose.yml`／`.env.example` 的 `BRIDGE_RESEARCH_*`（主控收尾單人窗口）；`AgentConsole/CLAUDE.md` 鐵律 7 加 ADR-XPLAT-017 §D7 引用句（主控）。

---

## 7. 勘誤記錄（凍結後的訂正；條文已原地訂正，被訂正的原文逐字保留於本表；走 `spec-refreeze`）

> 日期一律 2026-11-03（表內日期欄只寫月-日）；來源＝P0 各開發棒交卷的勘誤候選、SCG-4 一審（鍵 `agentconsole-research-to-prd-p0`）與主控裁決 D-67～D-85；§D9 的回寫素材取自 PKG-FE-C 與 PKG-FE-D 的量測證據。

<!-- 日期欄只寫月-日、不寫四位數年份：本表的列常同時引用含 passed／skipped 字樣的 reason 識別字，完整年份會讓 tools/check_pytest_baseline_sites.py 把該列誤判成測試基線數字，而它的站點棘輪不吃行內豁免標記；改寫識別字則失去可 grep 性，故改日期格式（年份見上方首句）。 -->

| 號 | 日期 | 條文 | 原文 → 改文 | 來源包／裁決號 |
|---|---|---|---|---|
| 1 | 11-03 | §D9 決策句與新增〈量測〉 | 原文：「bundle 增量於 P0 TCS 量測後回寫本節。」；再開症狀「首屏／路由 bundle 超 P0 TCS 量測定下的預算」（預算值未載） → 改文：回寫量測（相依版本與授權、`/research/[researchId]` 首次載入 JS 的 raw／gzip 前後值與歸因、200 KB PRD 的輸入延遲／Diff／預覽首次渲染、`RICH_EDIT_MAX_BYTES`＝30 KB、Diff 套件與自寫 `diffLines` 的組合、Mermaid `htmlLabels:false` 與淨化加強、頁殼改動態載入無效的實驗與劃界）；再開症狀補預算值（對改前基準 +20% 內） | FE-C E5（D9 組合）、FE-C 交卷素材、FE-D 交卷；TCS AT-960-17-1／17-4；SCG-4 F-14 |
| 2 | 11-03 | §D1 決策（新增「實作期訂正」） | 原文：「…每步 `maintain_context:false`…；請求 `env` 帶 `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`…、步驟 prompt 禁止背景任務與子代理。」（未載 run 級工具集的實際語法、步驟逾時預設、並行上限的處置、引擎 Brain） → 改文：加四點——run 級工具集為 `Read`／`Glob`／`Grep` 加 `Edit(//<工作區絕對路徑>/**)`（真機：`Write(<任何寫法>)` 一律被拒）；步驟逾時預設 600 秒；並行上限 1 的第二個 stage 一律 409、不排隊；研究 stage run 釘關引擎 Brain 並不傳 `MINIMAX_*` | D-74、D-75、D-67、D-79；BR-C（V-R1）；BR-A 交卷（6-4） |
| 3 | 11-03 | §D10 決策（新增「實作期訂正」） | 原文：「`mock-only` 時 UI 停用「啟動深研」並說明。」（未載預取行為） → 改文：`mock-only` 或劇本模式的預取一律不連網，改讀劇本 `prefetch` 夾具（紀錄 `outcome=OK`、`fetch_method=API`、`observed_by=BRIDGE`；DDL 的 `outcome` 列舉沒有 `MOCK`，D-78 原句「outcome 標 MOCK」依此訂正），無夾具＝`no_evidence` 但不外呼；切換劇本後 Bridge 容器須 `up -d --force-recreate` 並驗證容器內的值 | D-78（INT-06）；INT 重驗補記（〈注意〉1）；FIX-BR |
| 4 | 11-03 | §D5 決策（新增「實作期訂正」） | 原文：「游標欄位 `flow_step／flow_phase／flow_status／flow_detail`，只由 Bridge 在引擎動作同一交易寫入…」（未載失敗語意） → 改文：`flow_status` 優先序 `ESCALATED`＞`RUNNING`＞`FAILED`＞`WAITING_HUMAN`＞`IDLE`；stage run 失敗、取消或被回收＝`FAILED`＋`flow_detail`＝`exit_reason`、相態回退到可重入；不帶 `generation` 的 `reinit` 在 `flow_status=FAILED` 時一律可呼叫 | D-77、D-81（INT-02／04）；FIX-BR |
| 5 | 11-03 | §D7 決策末句；§4 誠實劃界 L-R10；§5 待實測 V-R1、V-R9 列 | 原文：「僅 Stack Exchange 官方頁無法抓取而未現查，沿保守節流初值並標「非事實宣稱」，V-R9 殘餘由 PKG-BR-B 落證（D-40）。」；L-R10「Stack Exchange 速率限制官方數值未現查…V-R9 殘餘落證」；V-R9「…現查，回填 NFR-R2P-03-6 與 allowlist 條目」 → 改文：V-R9 於 2026-11-03 結案（WebFetch 對該站回「unable to fetch」，改以 PowerShell 直接 GET 官方頁、HTTP 200，已回填；3 秒仍為保守取值）；V-R1 結案（真機結論＝`Edit(//…)`）；Architecture §12.1 L-R10 同步 | BR-B 交卷（V-R9 已結，commit `08f8cfea`）；BR-C（V-R1）；D-74 |
| 6 | 11-07 | §D5 決策（新增「實作期訂正」） | 原文：（無分流同步語意；游標只記 stage 失敗）「…`flow_status` 優先序…」 → 改文：`:route` 同步 200／502、牆鐘 300 s、console-api 讀取逾時 330 s；游標 `route／ROUTING／RUNNING`→`build／ROUTED／IDLE`｜`route／ROUTING／FAILED`；TCS 凍結後游標三段機制；BLOCKED_DB 重放後同交易重衍生 | D-105、D-125、D-128 |
| 7 | 11-07 | §D8 決策（新增「實作期訂正」） | 原文：「軌道 B「搬入」＝複製→逐檔 sha256 驗證→**原工作區原地保留**」（未載 worktree 位置與副本 raw 的版控處置） → 改文：`BRIDGE_WORKTREE_ROOT` 預設 `<BRIDGE_RESEARCH_ROOT>/_worktrees`、`git -c core.longpaths=true worktree add`；軌道 B 副本含 raw、以範本 `.gitignore` 排除入版控 | D-95、D-117 |
| 8 | 11-07 | §D14 決策（新增「實作期訂正」） | 原文：「範本清單取自 Bridge `app/research/scaffold_templates/<name>/` 目錄」（未載掃描根設定） → 改文：`BRIDGE_SCAFFOLD_ROOT` 無預設、新增 `BRIDGE_REPO_ROOT`；範本 Python 檔 `.tmpl` | D-96、⚖P1-18 |
| 9 | 11-07 | §D15 決策（GitHub token） | 原文：「GitHub token 由 console-api 取自 `system_configs` 加密欄」（D-98 另寫「不加 DDL」） → 改文：設定鍵 `research.github_token` 由 V20 只種一列設定（不加表） | D-98 訂正、D-132 |
| 10 | 11-07 | §D16 決策（git／gh 白名單） | 原文：允許集合「`add -A`（僅新專案根內）、…」；環境只移除 `BRIDGE_*`／`SDD_*`／`PYTHONPATH` → 改文：補 `add -- <明列路徑…>`（軌道 A 仍禁 `add -A`）、`worktree list --porcelain`、`-c core.longpaths=true`；環境另設 `GIT_AUTHOR_*`、`GIT_COMMITTER_*`、`GIT_TERMINAL_PROMPT=0`、`GCM_INTERACTIVE=never`、`GIT_OPTIONAL_LOCKS=0`；P1 白名單不含 P2 動詞（⚖P1-10） | D-99、D-128 F-13、⚖P1-10 |
