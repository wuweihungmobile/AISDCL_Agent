# 任務書 W3-B2：後端第二棒（Spring Boot 4.1／Java 21；Phase 4 專案執行 ＋ Phase 5 專案監控）

> 先讀 `COMMON_CONTEXT.md`（頂部〈本輪環境覆寫〉凌駕其後）、`AgentConsole/CLAUDE.md`、`AgentConsole/backend/README.md`、**W3-B1 的交卷（主控會貼給你）**，然後讀**契約 SSOT**：`AgentConsole/docs/02_architecture/API_Contract_P3-6.md` ＋ `openapi-p3-6.yaml`（衝突時以契約為準；契約沒寫到的再看 `W3_BACKEND_P3-6.md`〈已拍板決策〉與本檔〈補充裁決〉），**Bridge 真實契約** `AgentConsole/engine-bridge/README.md`（pause／resume／stop／restore 的前置狀態、SSE 封包、事件欄位）與 `engine-bridge/app/models.py`，最後讀本檔。
> 你在 W3-B1 交卷後的同一棵 backend 樹上續做；W3-B1 已放好 `AgentBridge` 介面（decompose／approve／sddCompile／health）、加解密、settings 讀取、audit、rate limit。

## 必讀 PRD 行段
§0.2～§0.4（58～103）、§5.3（821～1030）、§5.4（1030～1177）、§7.1.5～§7.1.7（1748～1790）、附錄 B 狀態機（2068～2108）。Architecture：§6(c)(d)（408～522）、§7（523～578）、§11.4（993～1038）、§12（1039～1069）。

## 範圍
1. **Flyway**：不需新表（V3 review_requests、V4 alerts 已在）；若需索引或欄位，開 `V7__*.sql`。
2. **執行 API**（契約 §1 `/api/v1/projects/{projectId}/execute`、`/api/v1/projects/{projectId}/executions`、`/api/v1/executions/{runId}/**` 全部）：
   - `ExecuteProjectUseCase`：OPERATOR 以上；專案與範圍內全部 Goal／Task `signedOff=true` 否則 409 `reason:"未經人工審批的草案不可執行"`＋`details.unsignedIds[]`；專案狀態只准 DRAFT／READY／FAILED／COMPLETED（EXECUTING 409）；範圍解析（ALL／SELECTED，所選 Goal 的依賴未選且未 COMPLETED → 409 `missing_dependencies`）；`DagService` Kahn 排序（策略 `execution.dagSchedulerStrategy`）；`PlaybookBuilder` 依契約 §3 欄位表（`step_id=T001…`、`goal_task_id=task.id`、prompt 組裝、`expected_output_regex`／`evaluator_command`／`max_retries`、`global_goal`、`global_invariants.max_retries_per_step`；每步 prompt > 20,000 字元 → 422 `prompt_too_long`）；`ConfigMaterializer`（Architecture §11.4 的 ✅ 列 → `config_overrides`／`env`；`claude.command` 取 settings `autoclaude.claudeCommand`，E2E 用 `aisdlc-mock-claude`；`MINIMAX_API_KEY` 解密後只進 `env`；測試旗標 `console.execution.mock-cli=true` 時 `env` 另帶 `MOCK_CLAUDE_*`）；建 `execution_runs` 列（只寫 D10 的 console 欄位；`run_number` 取號鎖專案列）並**先提交**；再 `AgentBridge.startRun` → 201 回 `ExecutionRunResponse`；409（`advisory_lock_held`）／422／逾時 5xx → 補償刪除剛建的列並轉 409／422／502。成功後專案 `EXECUTING`、範圍內任務 `QUEUED`、目標維持 PENDING 直到首任務 STARTED。
   - pause／resume／cancel／checkpoints／restore 直通 Bridge（Bridge 409 `invalid_state` 原樣轉 409 附 reason；resume／restore 前再做一次 signoff 校驗）。
   - `GET /executions/{runId}`（DB 列 ＋ Bridge `GET run` 合併；Bridge 不可達 → 200 且 `bridge.connected=false`）、`GET /executions/{runId}/steps?page&size&afterSeq`（讀 `console.execution_steps`，Bridge 寫）、`GET /executions/{runId}/dag`（run.dag ＋ 每節點現況）、`GET /projects/{projectId}/executions`（分頁）。
   - `POST /executions/{runId}/review/{reviewId}`（`reviewId`＝`review_requests.id`）：APPROVE → 若 run PAUSED 則 `:resume`；RETRY → 任務重置 QUEUED ＋ `restore` 到該步之前的最後一筆 checkpoint（`GET checkpoints` 取）；SKIP → 任務 SKIPPED ＋ `:resume`（若 Bridge 無法略過該步，記 🟡 並說明）；REJECT → `:stop`、run CANCELLED、目標 FAILED；寫 `decided_by/at`、status；204。
3. **事件消費與投影**：`RunEventConsumer`（每個活躍 run 一條虛擬執行緒）讀 Bridge SSE `GET /autoclaude/runs/{id}/stream?after=<last_seq>`；斷線以最後 seq 重連、缺口用 `GET …/events?after=&limit=` 回補；位移存記憶體（Redis 本輪不做，寫明）；每則事件依 Architecture §7.3 更新 Task／Goal／Project／run 讀模型（Bridge 的 `resume` 後同一步再發一次 STARTED 要冪等；`ESCALATION`／`halted` reason 判 ESCALATED 並建 review）；觸發告警評估；轉發給前端 SSE 訂閱者。後端啟動時掃 `RUNNING／PAUSED` 的 run 對帳 Bridge `GET run`（404 → alert「Bridge 失聯」）。
4. **自治等級審核閘** `ReviewGatePolicy`（契約 §3 決策表；Architecture §6(c).c.4「提前一步」）：Level 1 每步、Level 2 目標邊界、Level 3 目標完成／任務失敗、Level 4 僅 ESCALATED、Level ≥5 僅 run FAILED；pause 落在閘點、建 `review_requests`（kind）、對前端發 `review-request` 事件。最後一個目標的最後一步完成時 run 直接 COMPLETED、不建審核項。
5. **前端 SSE 端點**：`/api/v1/stream/executions/{runId}/logs`（`log`／`status-change`／`review-request`／`alert`）與 `/metrics`（`metric-update`／`token-update`／`progress-update`），`id:` 沿用 Bridge seq、後端自產事件用契約 §2 的子序號規則；`Last-Event-ID` 重播（來源：`execution_steps` ＋ Bridge `events` ＋ 本地 review／alert 表）；認證：`Authorization: Bearer` 與 `?access_token=` 皆收（擴充 `JwtAuthenticationFilter`，只對 `/api/v1/stream/**` 開放 query token）；每 15 秒 keep-alive 註解；PAUSED 不結束；終態送最後一則 `status-change` 後關閉。
6. **監控 API**（契約 §1 `/api/v1/monitor/**` 全部）：`metrics`（八項 KPI，Architecture §6(d) 計算式；支援 `runId`／`from`／`to`）、`token-trend`（`execution_steps.timestamp` 分桶 Σ tokens ＋ 預算線）、`task-trend`（依步驟狀態轉移分桶；同時給事件時間軸用的 `events[]`）、`alerts`、`alerts/{id}/acknowledge`、`logs`（時間／level／taskId／關鍵字篩選，分頁；來源 `execution_steps`）、`report?format=csv`（必做；`pdf` 做不完回 501 並在契約漂移寫明）；Agent 可用率＝對 Bridge `/health` 每 30 秒探測一次的環形緩衝（記憶體，容量 120）。
7. **告警規則六條**（PRD §5.4.4；閾值鍵見契約 §3）：Token 80% WARNING；超限 CRITICAL＋`:pause`；同目標連續 3 次失敗 CRITICAL＋`:pause`＋建 review；Agent 無回應（逾 `monitor.alertAgentTimeoutSec` 無事件且探測失敗）CRITICAL；單任務逾 `agent.taskTimeout × multiplier` WARNING；目標內重試率 > 50% WARNING。同規則＋同對象在被確認前不重複產生；每則事件評估一次，另有 30 秒排程 tick 處理純時間型規則。
8. **OpenAPI 對帳**：同 W3-B1——springdoc 產物 vs `openapi-p3-6.yaml` 逐端點比對，差異列在〈契約漂移〉。

## 補充裁決（主控已定）
- Bridge 的 SSE 消費用 JDK `HttpClient`（`BodyHandlers.ofLines()`）即可，不加新依賴；前端 SSE 用 Spring MVC `SseEmitter`（虛擬執行緒）。
- 整合測試的 Bridge 替身：在 `src/test` 放一個**測試用 Spring Boot 迷你 Bridge**（`@RestController`，隨機埠；提供 `POST /autoclaude/runs`、`:pause|:resume|:stop`、`GET run`、`GET events`、`GET stream`（`SseEmitter` 依腳本發事件）、`GET checkpoints`、`restore`、`/health`），可用腳本控制事件序列與時序，用來驗投影、審核閘「提前一步」、重連回補、補償刪除、告警。不要用 WireMock。
- **真 Bridge 冒煙一次（必做、親跑）**：PG 容器 ＋ Bridge（`D:\CursorProject\AISDCL_Agent\.venv\Scripts\uvicorn.exe app.main:app --port 18081`，`Push-Location D:\CursorProject\AISDCL_Agent\AgentConsole\engine-bridge` 下起、`run_in_background`，環境變數 `BRIDGE_DB_DSN` 指同一顆 PG、`BRIDGE_DB_SCHEMA=console`、`BRIDGE_ALLOWED_PATH_ROOTS` 含你的測試專案目錄）＋ backend bootRun（`ENGINE_BRIDGE_URL=http://127.0.0.1:18081`、`console.execution.mock-cli=true`、settings `autoclaude.claudeCommand=aisdlc-mock-claude`）：建專案（含 2 個目標各 2 個任務，passCriteria 內含 `[T_DONE]` 之類的關鍵字，expectedOutputRegex 對應）→ Level 3 execute → 讀 `GET /api/v1/stream/executions/{runId}/logs`（`curl.exe -N -H "Authorization: Bearer …"` 貼前 10 行，含 step 事件）→ 等 COMPLETED → `GET /executions/{runId}` 貼狀態、`GET metrics` 貼數字；再跑一次 Level 1：第一步後 PAUSED＋review-request，APPROVE 後跑完；再跑一次 cancel。交卷前把 Bridge／backend／PG 全部收掉並貼 `Get-Process` 結果。
- 專案 `executionPath` 在本機模式是主機路徑（Windows 含磁碟機代號）；測試用的專案目錄建在你的 scratchpad 子目錄，並把它放進 `BRIDGE_ALLOWED_PATH_ROOTS`（`;` 分隔）。
- `review-request` 事件由後端自產（Bridge 不發）；`stepId`／`taskId`／`goalId`／`kind`／`reason`／`requestedAt` 依契約 §2。
- Redis 不做（位移與探測緩衝全在記憶體），在〈沒做／偏離〉寫明並標 RTM 相關列 🟡。

## 測試要求
- 單元：`PlaybookBuilder`（step_id／prompt 組裝／goal_task_id／規則對映／20,001 字元 422）；`DagService` 三種策略；`ReviewGatePolicy` 決策表（Level 1～6 × STARTED／COMPLETED／FAILED／ESCALATED／run FAILED → pause？kind？）；六條告警規則各一正一反；事件投影表（§7.3 每列一支，含重複 STARTED 冪等）；SSE 序號與重播切片；`ConfigMaterializer` 對映（含 ⛔ 鍵不物化、apiKey 只進 env）。
- 整合（Testcontainers PG18 ＋ 迷你 Bridge）：契約 §5 的執行類情境全部（execute 409／201、投影到 COMPLETED、Level 1 閘、ESCALATED 審核 RETRY／SKIP、cancel、restore、斷線重連回補、補償刪除、token 告警＋自動 pause、連續失敗告警、rate limit 不受影響）；SSE 端點以 `WebTestClient` 或 `RestClient` 串流讀取驗 `id:` 與 `Last-Event-ID`；`GET /executions/{runId}` 在迷你 Bridge 關掉時 `bridge.connected=false`。
- 真 Bridge 冒煙三條（見上）逐字貼證據。
- `jacocoTestCoverageVerification` ≥ 80%；ArchUnit；Checkstyle 0 warning。

## 閘門
同 W3-B1 的 `clean build`／JaCoCo 指令；加 `/v3/api-docs` 的 Phase 4／5 端點清單；真 Bridge 冒煙證據；`git status --porcelain` 全部落在 `AgentConsole/backend/**` 與 `rtm_backfill_W3B2.md`。

## RTM 回填
寫到 `AgentConsole/docs/06_quality/rtm_backfill_W3B2.md`（同 W3-B1 格式），涵蓋 US-E-01～11（BE 側）、US-M-01～10（BE 側）、API-EXE-*、API-SSE-*、API-AUT-*、API-DAG-*、API-MON-*、API-ALR-*、BR-* 中你實際消費的 Bridge 行為列、NFR-OBS-01。

## 交卷
照 COMMON_CONTEXT〈交卷格式〉，另加〈契約漂移〉與〈給前端 W4-F2 的提醒〉（SSE 事件實際欄位、重連建議、DAG 回應形狀、review 動作後的狀態時序）。不准 commit／push、不派子 agent、不留背景行程。

## 主控裁決補充（2026-10-15，依獨立 Architect 審查 AR-xx；與本檔上文衝突時以本節與契約 v1.1 為準）
- **Flyway V7 必做**（契約 §0.5）：`run_token_samples`、`review_requests`／`alerts` 的事件錨點欄位、`execution_runs.console_last_seq`、告警未確認去重的 partial unique index（上文「不需新表」作廢）。
- **照契約的字面**：`step_id=G<g>-T<t>`；mock 旗標＝`console.execution.mock-env`（map，只在 e2e／test profile 載入）；消費位移存 DB `console_last_seq`；探測環 2,880 筆（24 小時）；審核 `SKIP`＝開後續批次（回應標頭 `X-Follow-Up-Run-Id`），不是 `:resume`；Token halt 不判 ESCALATED（只有 ESCALATION 才判）；logs／SSE 重播來源依契約 §2；啟動對帳 Bridge 404 依契約（WARN，不發 alert）。
- **Bridge P1（AR-01）**：Bridge 在 DB 模式對 PAUSED run 做 restore 會自撞 advisory lock——主控已另派 Bridge 修復者修 `reacquire_lock`／`acquire`；你依契約 E2E-07 實作「PAUSED 可 restore」；若你開工時 Bridge 修復尚未落地，冒煙改以終態 restore 代替並在交卷寫明。
- **SSE（AR-02／AR-03）**：`/metrics` 收斂快照的事件 id 互異（`<S>.1` progress-update、`<S>.2` token-update、`<S>.3` metric-update；終態 204 條件見契約 §2.6），同一條串流 id 嚴格遞增無重複；框架用 Spring `SseEmitter` 即可（冒號後空白不保證，QA 以解析後欄位斷言）。
- **nginx（AR-05）**：你的檔案範圍放寬到 `AgentConsole/docker/nginx/conf.d/default.conf` 的 `/api/v1/stream/` location（`proxy_buffering off`、`proxy_read_timeout 3600s`、`proxy_http_version 1.1`）與 `AgentConsole/docker/nginx/nginx.conf` 的 `log_format`（遮罩 `access_token`：改記 `$uri` 或 map 後的 query）；後端任何存取日誌不得輸出含 `access_token` 的 query string。
- **通知摘要（AR-08）**：把探測環接到 `GET /notifications/summary` 的 `bridgeConnected`／`bridgeCheckedAt`（B1 先回 null，同一支 controller）。
- **人工判定優先（AR-11）**：被 REJECT／SKIP 標過的目標不被 R-goal 重算覆蓋；順序＝先重算、再套人工判定。
- **補償刪除（AR-15）**：守門改「該 run 尚無 `execution_steps`」，不看狀態（`spawn_failed` 時 Bridge 已把列標 FAILED，仍要刪）。
- **冒煙三條的自治等級**：多目標專案在 Level 3 會於目標邊界 PAUSED（GOAL_COMPLETED 審核）——「一路跑到 COMPLETED」用 Level 4；Level 3 另驗一次「目標邊界 PAUSED → APPROVE → 跑完」；Level 1 驗第一步後 PAUSED。
- **SSE 完成時的 ASYNC dispatch（TBC-1）**：`SseEmitter` 完成會走 ASYNC dispatch，`JwtAuthenticationFilter` 是 `OncePerRequestFilter`；設定 `dispatcherTypeMatchers(DispatcherType.ASYNC).permitAll()` 或覆寫 `shouldNotFilterAsyncDispatch`，交卷貼「無 AccessDenied 錯誤日誌」的證據。
- **E2E／冒煙的 Bridge 啟動（AR-12、TBC-2）**：啟動前 `$env:PATH = 'D:\CursorProject\AISDCL_Agent\.venv\Scripts;' + $env:PATH`；settings `autoclaude.claudeCommand` 用絕對路徑 `D:\CursorProject\AISDCL_Agent\.venv\Scripts\aisdlc-mock-claude.exe`（V5 的 validation_rule 要允許 Windows 絕對路徑）；`$env:AUTOSDD_QUOTA_CACHE_DIR='<E2E_ROOT>\quota-cache'`；清掉 `AUTOSDD_*`（`AUTOSDD_QUOTA_CACHE_DIR` 除外）／`AUTOCLAUDE_*`／`MINIMAX_*`／`MOCK_CLAUDE_*`；引擎沒有演化開關鍵（SA 現查 config.py／main.py）——E2E 關閉演化＝執行類情境 `model.apiKey` 為空＋Bridge 環境無 `MINIMAX_*`（契約 D-58）。
