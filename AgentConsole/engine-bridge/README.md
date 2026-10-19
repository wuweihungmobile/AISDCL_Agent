# Engine Bridge（FastAPI 旁車）

把兩個**純 CLI** 引擎（`AutoClaude/`、`AISDLC_SDD/`）包成 REST + SSE，給 Spring Boot 後端呼叫（PRD §0.2）。
單一服務、單一埠 `8081`，以路徑前綴區分：`/autoclaude/*`、`/sdd/*`、`/health`、`/health/deep`。**最小侵入白名單**（ADR-XPLAT-016 §11；2026-10-17 整合輪 115 取代原「零侵入」）：兩個引擎只准改該 ADR 列出的檔，其餘仍由本旁車包裝；SDD FSM 的寫入一律經 `FSMRuntime` CLI 子行程，Bridge 原始碼不開寫 `FSM-STATE-*.yaml`（見〈SDD 整合〉）。

```
app/main.py        FastAPI app／lifespan（啟動做孤兒回收、起資源取樣器）／/health／/health/deep
app/settings.py    環境變數 → Settings        app/models.py    請求／回應模型（照 API 契約）
app/security.py    NFR-SEC-03/04 消毒鏈       app/runner.py    spawn `python -m autoclaude`、監督、pause/resume/stop/restore
app/events.py      events.jsonl + 記憶體環    app/logparse.py  引擎 stdout 步驟訊號解析 + 步驟狀態機
app/checkpoints.py 歷史快照 + 引擎格式寫入    app/locks.py     並發互斥（行程內 + PG advisory lock）
app/db.py          DB 模式狀態鏡射            app/decompose.py 目標拆解（GoalDecomposer）+ 草稿存檔
app/procutil.py    行程樹治理（psutil）       app/mock_claude.py E2E 用的確定性 claude 替身（console script）
app/health.py      /health/deep 深度探針      app/tracing.py   X-Trace-Id 中介層＋contextvar（traceId 貫穿）
app/logsetup.py    日誌格式（每行 trace_id）＋BRIDGE_LOG_DIR 滾動檔      app/resources.py 引擎行程樹資源取樣（`resources`；D-12）
app/routers/       autoclaude.py、sdd.py
app/sdd_cli.py     唯一的 FSM 寫入出口：FSMRuntime CLI 子行程（固定環境、動詞白名單、20 秒逾時、rc→HTTP、`(狀態目錄, 專案鍵)` 互斥鎖）
app/sdd_state.py   FSM 狀態檔唯讀存取（tail／凍結階段／委派引用／恢復指令）   app/sdd_sync.py  委派同步純函式（reason 組字、終態對映、預檢表、回收點判定）
app/sdd_run.py     批次的 SDD 側（路徑閘、三點摘要預檢、FSM 寫入、補償、`resume`／`restore` 重驗）    app/sdd_adapter.py AutoClaude adapter 的呼叫接縫
app/fsm_names.py   FSM 專案名規則（`sanitize_component` 的逐字鏡像＋輸出域判準）    app/spec_digest.py 規格摘要（換行正規化的 UTF-8 sha256）    app/rtm.py `GET …/rtm`
app/fsm_phase.py   `current_state` → `phase{name,order,blocking,observation}` 純函式（契約 §3.1.5；W4 dogfood 由真 haiku 寫出、SCG-4 審查通過後搬入）
```

## 前置需求

Python 3.11、[uv](https://docs.astral.sh/uv/)。Docker 只在建映像／DB 整合測試時需要。

## 本機模式

安裝（**用 monorepo 根層 `.venv`**——repo 單一 venv 規則，pre-commit 的 stray_venv 閘會擋其他 venv；AutoClaude 已由根層 `tools/dev_start` 裝入，這裡只補 Bridge 自身）：

```bash
# bash（相對於 monorepo 根）
cd AgentConsole/engine-bridge
. ../../.venv/bin/activate
uv pip install -e . -e ../../AutoClaude
```

```powershell
# PowerShell（相對於 monorepo 根；不用裸 cd）
Push-Location AgentConsole\engine-bridge; ..\..\.venv\Scripts\Activate.ps1; uv pip install -e .; Pop-Location
```

啟動與驗證（另開一個終端機打 `/health`）：

```bash
uvicorn app.main:app --port 8081                # 或 python -m app.main（讀 BRIDGE_HOST／BRIDGE_PORT）
curl -s localhost:8081/health
```

```powershell
Push-Location AgentConsole\engine-bridge; ..\..\.venv\Scripts\Activate.ps1; uvicorn app.main:app --port 8081; Pop-Location
Invoke-RestMethod http://localhost:8081/health
```

`/health` 回 `{"status":"ok","bridge_instance":…,"engines":{"autoclaude":{"ok","version"},"sdd":{"ok","latest"}},"db":{…}}`。
`status` 只代表 Bridge 自己活著；引擎／DB 的狀況看 `engines.*.ok`、`db.ok`。**必須單一 worker**（run 登記表與行程監督在記憶體內）。

`GET /health/deep`（免認證，契約 v1.2 §3.1.1；QA DEF-AC-003）是**深度探針**：把「引擎真正依賴的外部條件」逐項實測——① `git --version`（subprocess，逾時 5 秒）、② `import autoclaude`、③ 在 `ENGINE_WORKSPACE` 建立並刪除暫存檔（可寫）、④ DB ping（只有設了 `BRIDGE_DB_DSN` 才做，否則 `ok:null`）、⑤ SDD 樹（W7 D-17，**只當資訊、不影響 200／503**，規則見下）。前四項全部通過回 **200** `{"status":"ok","checks":{"git":{"ok":true,"version":"git version 2.47.3"},"autoclaude":{"ok":true,"version":"…"},"workspace":{"ok":true},"db":{"ok":null},"sdd":{"ok":true,"latest":"AISDLC_SDD_v0.30"}}}`；前四項任一失敗回 **503** `{"status":"degraded","reason":"git: 找不到 git 執行檔","checks":{…}}`（失敗項 `ok:false` 並各附 `reason`，頂層 `reason` 以「；」連接前四項的失敗，不含 `sdd`）。為什麼有 `/health` 還要它：Docker 映像曾缺 `git`，`/health` 永遠 200、容器永遠 healthy，任何批次卻一律 `FAILED`。docker compose 與映像內建的 healthcheck 打 `/health/deep`；契約 v1.4（D-17）起 **console-api 的探測環預設也打它**（`autoclaude.healthCheckPath`；成本是每 30 秒 spawn 一次 git、建刪一個暫存檔，對單一 Bridge 可忽略）。淺層 `/health` 的形狀不動。

第五項 `checks.sdd`（W7 D-17）的形狀是 `{"ok": true／false／null, "latest": "<目錄名>"／null, "reason": "…"}`（`reason` 只在 `false`、`null` 時出現）。🔴 **它只當資訊：不論 `ok` 是什麼，整體 `status` 與 HTTP 狀態都只由 git／autoclaude／workspace／db 四項決定**，頂層 `reason` 也只列那四項的失敗（契約 v1.4 §3.1.1，主控裁定）。為什麼：SDD 是選用引擎，它壞了要顯示在 Console 的 SDD 卡，不該讓 Agent 可用率下降或誤報 `AGENT_UNRESPONSIVE`——console-api 的探測環與 compose 的 healthcheck 都打這一支，503 會被當成 Bridge 不可用。

| `SDD_ROOT`（含預設位置）的狀況 | `ok` | 整體 `status`／HTTP |
|------|------|------|
| 沒設、預設位置也找不到 `AISDLC_SDD`（Bridge 照樣能跑 AutoClaude 的批次；`/sdd/*` 會回 503） | `null`（`latest` 為 `null`） | 不受影響 |
| 設了但不是目錄（不存在或是檔案） | `false`（`latest` 為 `null`） | 不受影響：前四項健康就是 200 `ok` |
| 是目錄，且有 `build/reports/fsm`，**或**有版本入口文件 `AISDLC_SDD_INIT.md` | `true`，`latest`＝目錄名 | 不受影響 |
| 是目錄，兩者都沒有（空目錄、唯讀掛載沒掛到東西） | `false`（`latest` 為目錄名） | 不受影響 |

為什麼入口文件也算數、不能只看 `build/reports/fsm`：LATEST 版的 `build/reports/` 被 git 忽略（`AISDLC_SDD/.gitignore`），入庫檔數為 0，所以**全新 clone 沒有 FSM 狀態目錄**——那是跑過 SDD runtime 才會產生的執行期產物，不是「SDD 樹有沒有掛上」的證據。只看它的話，Console 的 SDD 卡會對一份完好的全新 clone 顯示失敗。

## 環境變數

| 變數 | 預設 | 說明 |
|------|------|------|
| `BRIDGE_HOST` | `127.0.0.1` | 僅 `python -m app.main` 使用（Docker CMD 另帶 `0.0.0.0`） |
| `BRIDGE_PORT` | `8081` | |
| `ENGINE_WORKSPACE` | `<engine-bridge>/.workspace` | 每個 run 一個子目錄（見〈資料落地〉）；已 gitignore |
| `AUTOCLAUDE_ROOT` | `<monorepo>/AutoClaude` | 只供 `/health` 顯示 |
| `SDD_ROOT` | `<monorepo>/AISDLC_SDD` 下 `AISDLC_SDD_v*` 數字最大者 | `/sdd/*` 讀取的版本目錄，**或含多個版本的父目錄**（取數字最大者；Docker 把整個 `AISDLC_SDD` 唯讀掛成 `/sdd` 並設 `SDD_ROOT=/sdd` 即可）；找不到時 `/sdd/version`、`/sdd/fsm` 回 503 |
| `BRIDGE_DB_DSN` | （未設＝純檔案模式） | PostgreSQL DSN；設了才寫 DB、鎖才跨實例 |
| `BRIDGE_DB_SCHEMA` | `console` | **Console 九張表所在的 schema**。DB 模式的 SQL 一律用 schema 限定名（`console.execution_runs`、`console.execution_steps`、`console.checkpoints`），以 `psycopg.sql.Identifier` 引用；AutoClaude 自己的 alembic 在 `public` 有同名表，所以不可用 `public`。advisory lock 不是表，不受影響 |
| `BRIDGE_INSTANCE` | `<hostname>-<pid>-<uuid8>` | 本實例識別（≤100 字，寫進 `execution_runs.bridge_instance`） |
| `BRIDGE_STOP_GRACE_SECONDS` | `30` | stop／pause 送終止訊號後，等多久才升級強殺 |
| `BRIDGE_ALLOWED_PATH_ROOTS` | 工作區 + monorepo 根 | `execution_path`／`spec_dir` 必須落在其下；以 **`os.pathsep`** 分隔（POSIX `:`、Windows `;`）；不接受檔案系統根 |
| `BRIDGE_OUTBOUND_ALLOWLIST` | `api.minimax.io,api.minimax.chat,localhost,127.0.0.1` | 外呼 host 白名單（逗號分隔，精確比對） |
| `BRIDGE_SDD_WRITE_TOKEN` | （未設＝SDD 寫入面停用） | SDD 寫入面權杖（ADR-XPLAT-016 §9；backend 與 Bridge 同值，HTTP 標頭 `X-Bridge-Token`）。未設：`:freeze` 與含 `sdd` 區塊的建立／續跑回 503 `sdd_write_disabled`，不含 `sdd` 的 run 照舊；設了但**短於 32 字元或仍是 `<…>` 佔位＝啟動即 `SettingsError`**（不靜默退回停用）。repo 內不放任何真值；產生方式見 `AgentConsole/.env.example`。它不會進引擎與 FSM CLI 子行程，也不出現在稽核與任何回應 |
| `BRIDGE_LOG_DIR` | （未設＝不寫檔） | 有值時，日誌另寫成滾動檔 `<dir>/bridge.log`（UTC 午夜切檔、保留 7 份）；stderr 的日誌照舊。目錄建不出來或不可寫只在 stderr 留一則警告，Bridge 照常啟動。docker compose 設 `/app/logs`（與 backend 共用 `app_logs` 卷）。見〈追蹤碼與日誌〉 |
| `BRIDGE_TEST_DSN` | （測試用） | 設了才跑 `tests/test_db_integration.py` |

## API（契約逐字；補充與落地差異見 `AgentConsole/docs/02_architecture/Architecture.md` §10）

`POST /autoclaude/runs`（201／409 `advisory_lock_held`＋`holder_run_id`／422；本文含 `sdd` 區塊時另要 `X-Bridge-Token`，201 多 `warnings[]`）、`POST /autoclaude/runs/{id}:pause|:resume|:stop`（202；`:resume` 對含 `sdd` 的 run 要 `X-Bridge-Token`）、
`GET /autoclaude/runs/{id}`、`GET …/rtm`（追溯覆蓋，唯讀；見下）、`GET …/stream?after=`（SSE，亦認 `Last-Event-ID`）、`GET …/events?after=&limit=`、`GET …/checkpoints`、`POST …/restore`（對含 `sdd` 的 run 要 `X-Bridge-Token`）、
`POST /autoclaude/decompose`、`POST /autoclaude/decompose/{draft_id}:approve`、`GET /sdd/version`、`GET /sdd/fsm`、`GET /sdd/fsm/{project}`（兩者皆認選填 `root`）、`POST /sdd/fsm/{project}:freeze`（人工閘寫入，要 `X-Bridge-Token`）、`POST /sdd/compile`、`GET /health`、`GET /health/deep`。
錯誤封包一律 `{"code":<狀態>,"reason":"…",…}`；422 另帶 `violations`（逐項列出違規欄位與字元）。互動式文件：`http://localhost:8081/docs`。

### 資源取樣：`GET /autoclaude/runs/{id}` 的 `resources`（契約 v1.3 §3.1.2；W7 D-12）

回應多一個欄位 `resources`：`{"cpu_percent": 12.3, "rss_bytes": 104857600, "process_count": 3, "sampled_at": "2026-10-16T04:30:05.123456+00:00"}`，或 `null`。

- `cpu_percent`＝**整機正規化**：引擎行程樹（`python -m autoclaude` 與它的全部子孫，含 claude 或 mock claude；不含 Bridge 自己、也不含別的 run）各行程 `cpu_percent` 的總和 ÷ 邏輯核心數，夾在 0.0～100.0、小數 1 位（100＝整台機器所有邏輯核心被占滿，與 `top` 的單核 100% 不同）。`rss_bytes`＝各行程 RSS 的總和（共用頁會重複計入，是上界估計）。`process_count`＝取樣成功的行程數（含根）。`sampled_at` 帶 offset（Bridge 一律 UTC）。**不含** pid、命令列、環境變數。
- 何時是 `null`：引擎行程樹不存活（尚未 spawn、**PAUSED**、任何終態、行程已消失）、還沒有第一筆樣本、或最近一筆超過 **15 秒**沒更新（取樣器卡住時寧可回 null，也不回過期的數字）。resume／restore 後根 pid 換了，舊樣本不會被沿用。
- 怎麼取樣：`app/resources.py` 的背景執行緒（lifespan 在孤兒回收後啟動、關閉時先停）**每 5 秒**對每個存活的 run 取一筆，只留最近一筆；請求路徑只讀那一筆，**從不取樣、不阻塞**。新 spawn 的 run 會喚醒執行緒立刻補一筆（CPU 為 0.0：沒有上一次的基準）。
- 🔴 陷阱：`psutil.Process.cpu_percent(interval=None)` 是「與同一個 Process 物件上一次呼叫之間」的差值，而 `children()` 每次都回新物件——所以取樣器**跨 tick 持有每個 pid 的 `Process` 物件**（以 pid＋create_time 判斷是不是同一個行程），每個 tick 重建物件會讓 CPU 永遠是 0.0。
- 單一行程取不到（剛結束、權限不足）只略過它；取樣器自己的例外只記日誌（同處最多每 60 秒一行，且只記例外類別）。Windows 行為＝只走 psutil；用 venv 的 `python.exe` 啟動的行程會多一層啟動器殼，`process_count` 因此比直覺大。

### SDD 狀態：`GET /sdd/fsm`（清單）與 `GET /sdd/fsm/{project}`（W7 D-16）

資料來源是 `<狀態目錄>/FSM-STATE-<project>.yaml`，狀態目錄預設 `<SDD_ROOT>/build/reports/fsm`；選填 query `root`（專案根，須在 `BRIDGE_ALLOWED_PATH_ROOTS` 之下）改讀 `<root>/build/reports/fsm`。`SDD_ROOT` 無效（沒設、不是目錄）不論有沒有 `root` 一律 `503 sdd_unavailable`。
`project` 的規則見〈SDD 整合〉的專案名規則（v1.5 起不再是 `^[A-Za-z0-9._-]{1,128}$`；CJK、空白、括號、`+`、`@` 的專案名都列得出、讀得到）。

- `GET /sdd/fsm` → `{"root":"AISDLC_SDD_v0.30","projects":[{"project","source","current_state","updated_at"}],"errors":["…"]}`。`project`＝檔名去掉 `FSM-STATE-` 與 `.yaml`（就是 `GET /sdd/fsm/{project}` 吃的那個鍵）；依 `project` 不分大小寫排序；名稱不合白名單、讀不動（非 UTF-8、不是 YAML、巢狀過深）、缺 `fsm_state` 根節點、或 symlink 指到 `fsm` 目錄之外的檔名放進 `errors`，不影響其他檔。`build/reports/fsm` 不存在（全新 clone 沒有，原因見上方 `/health/deep` 第五項的說明）回 **200 空清單**，不是錯。
- `GET /sdd/fsm/{project}`：既有 8 個欄位不動，另增（只增不減）：
  - `human_pending` ＝ `{"count": N, "items": [尾 5 筆，原樣]}`，來源 `human_pending_tracking`。**真實檔裡它是單一 dict**（`entered_at`、`reminder_sent_at`、`reminder_hours`、`escalation_hours`；離開 HUMAN_PENDING 時 `entered_at` 被清成 null）：`entered_at` 有值＝正在等人（`count` 1、`items` 為該 dict 原樣），沒有＝`count` 0、`items` 空；若哪天改成 list，則 `count`＝筆數、`items`＝尾 5 筆。
  - `retry_history` ＝ `{"count": N, "last": 尾 1 筆｜null}`。**真實檔裡它是 dict of dict**，以重試閘為鍵（`SCG_VALIDATION`、`PR_REVIEW`、`RTM_VERIFY`），每個閘有 `current_count`、`max_limit`、`history`（list，每筆 `attempt`、`date`、`failure_reason`、`scg_gate`）：`count`＝各閘 `history` 筆數的總和，`last`＝全部筆中 `date` 最晚者（同時刻取後出現的）原樣再加一個 `gate` 欄；若改成 list，則取筆數與尾端一筆。
  - `rtm_coverage` ＝ 檔內 `fsm_state.rtm_coverage` 原樣，沒有這個鍵就是 `null`（真實狀態檔沒有任何 RTM 覆蓋數值，所以目前恆為 `null`）。
  - v1.5 再增：`phase`（`{name,order,blocking,observation}` 物件，永遠出現、**不是 `null`**：`current_state` 經 `app/fsm_phase.py` 純函式投影——主路徑八個階段 `order` 1～8、觀測態 `observation=true` 並取回歸階段、阻塞態 `BLOCKED`／0、過渡態 `TRANSIENT`／0；缺值、非字串或不認得的狀態是 `UNKNOWN`／0，不拋例外；`GET /sdd/fsm` 的清單項不帶它）、`escalation_history`（尾 5 筆原樣）、`escalation_provenance`（檔內原樣，沒有就 `null`；辨識「這是委派失敗」要讀它的 `source == "autoclaude_delegated_failed"`）、`fsm_project`（狀態檔名裡**淨化後的鍵**；`project` 是檔內原名，兩者可不同）、`recovery`（只在 `ESCALATION`／`ESCALATION_FINAL` 時出現、其餘情形**鍵缺席**而不是 `null`：`{"target","powershell","posix"}`，一行可複製的人工恢復指令，**恢復只有人能做、留在 SDD session**，Bridge 沒有恢復動詞）。🔴 `recovery` 與 `escalation_provenance`、`autoclaude_delegated_tracking` 在人工恢復後都不會被清除：判斷「現在有沒有未解的委派失敗」要看 `current_state` 屬 ESCALATION 類且 `escalation_history[-1].resolved_at` 為空。Docker 內執行時，指令裡的路徑是**容器內**看到的路徑，在主機上貼用前要自己換成主機路徑。
- 找不到檔、或 `project` 不在淨化輸出域 → 404 `fsm_not_found`（回報的是使用者問的名稱）；原名含 `/`（單一路徑段的 `{project}` 對不到路由，見下）→ 框架預設的 404 `{"detail":"Not Found"}`，**沒有 `reason`**、不是 Bridge 的錯誤封包；檔存在但讀不動 → 422 `fsm_state_unreadable`。

### 追溯覆蓋：`GET /autoclaude/runs/{id}/rtm`（ADR-XPLAT-016 §8.5；契約 v1.5 §3.1.4 (f)）

唯讀、不需權杖的**諮詢視圖**：讀該 run 工作區 `engine/checkpoints/rtm/` 下最新（修改時間，同刻取檔名較大者）的 `RTM-COVERAGE-*.yaml`（引擎的 `RtmWritebackPlugin` 只在 run **正常走完**時寫；`.jsonl` 歷史與 `RTM-GAP-*.md` 不讀）。回應 `{"scenario","spec_digest","at":{"passed","total","pct","unmapped"},"ac":{"covered","total","pct"},"failed_at_ids":[…],"weak_regex_at_ids":[…],"unmapped_at_ids":[…],"fully_covered":bool,"advisory":true}`；`advisory` 恆 `true`——它**不覆寫**人工 RTM，真正的閘是 SCG-4 的獨立審查。`unmapped_at_ids`／`summary.unmapped_at` 是 §8.5 新增欄，舊報告沒有它們時讀成 `[]`／0。run 不存在 404 `run_not_found`；沒有報告（沒啟用 SDD 治理、run 還沒結束、run 不是正常走完——例如引擎升級失敗）404 `rtm_not_found`（沒有報告與「覆蓋為零」是兩件事）；壞檔（讀不動、不是 YAML 映射、缺 `summary` 或核心數字）422 `rtm_unreadable`。

## SDD 整合（ADR-XPLAT-016「最小侵入白名單」；契約 v1.5）

### 寫入面與權杖

Console 路徑上 Bridge 對 SDD 的**寫入面**只有三處，全部要標頭 `X-Bridge-Token`（值＝環境變數 `BRIDGE_SDD_WRITE_TOKEN`）：

| 端點 | 何時要權杖 | 做什麼 |
|------|-----------|--------|
| `POST /sdd/fsm/{project}:freeze` | 一律 | 人工閘：`HUMAN_PENDING`→`SPEC_FROZEN`（CLI `spec-frozen --digest`；摘要由 CLI 算並寫進 `frozen_stages[].spec_doc_digests`） |
| `POST /autoclaude/runs`（本文含 `sdd` 區塊） | 含 `sdd` 才要 | 預檢→取鎖→FSM 寫入（談判、`delegate-enter`）→建 run→spawn；不含 `sdd` 的請求與 v1.4 完全相同、不需權杖 |
| `POST /autoclaude/runs/{id}:resume`、`…/restore` | 該 run 的 `RunRecord` 帶 `sdd` 才要（D-115-18） | 它們會 `delegate-enter`＝FSM 寫入；缺／錯同建立；不帶 `sdd` 的 run 照舊 |

- 未設權杖＝**503 `sdd_write_disabled`**（整個寫入面停用，fail-closed）；標頭缺或不符＝**403 `sdd_write_forbidden`**（缺與錯同一個 reason，不給探測者區分；`hmac.compare_digest`）。權杖檢查**先於**一切會碰檔案系統或 FSM 的動作。
- 被拒與成功都記一筆請求層稽核 `sdd_write`（verb＝`freeze`｜`run`｜`resume`｜`restore`｜`reclaim`｜`compensate`；`ok`｜`rejected:<reason>`；`trace_id`；續跑類另帶 `run_id`），**絕不記權杖值**。
- `BRIDGE_SDD_WRITE_TOKEN` 不會進引擎與 FSM CLI 子行程：`_child_env` 先剝除繼承來的 `BRIDGE_SDD_WRITE_TOKEN`／`SDD_STATE_DIR`／`SDD_PROJECT` 再**只對含 `sdd` 區塊的 run** 設 `SDD_PROJECT=<鍵>`；請求層 `env` 也不得設這三個名字（422 `forbidden_name`，大聲而不是靜默覆蓋）。
- 🔴 誠實劃界：權杖只封住 **Bridge 的 HTTP 寫入面**。引擎子行程內的 AI 步驟仍可自己執行框架的 FSM CLI；縱深在於不注入 `SDD_STATE_DIR`、批次期間 FSM 在 `IMPLEMENTATION`／`AUTOCLAUDE_DELEGATED`（`spec-frozen` 轉態不合法）、凍結綁內容（竄改規格可偵測）。不防禦主動對抗的 AI。

`:freeze` 的檢查順序（固定）：①本文格式（422 `invalid_request`）②權杖（503／403）③`approver`／`reason` 清理（422 `sdd_invalid_argument`）④`root`（422 `sanitization_failed`）⑤專案與狀態檔（404／422）⑥`docs[]` 逐項（`absolute`／`contains_dotdot`／`outside_root`／`not_found`／`duplicate`／`invalid`）加含官方命名的 TCS（`missing_tcs`；422）⑦前置狀態須為 `HUMAN_PENDING`（409 `fsm_state_conflict`）⑧`expected_digests`（核准人當時看到的摘要 vs 現檔；不符 409 `spec_digest_changed`／`pair=expected_vs_file`）⑨CLI 記錄凍結。成功回應＝凍結後重讀的狀態（與 `GET` 同形）加 `stage`（省略＝`Stage-<n>`，n＝已凍結階段數＋1，`kind: refreeze` 的重記條目不計）與 `spec_doc_digests`。

```bash
curl -s -X POST "http://localhost:8081/sdd/fsm/<project>:freeze" -H "X-Bridge-Token: $BRIDGE_SDD_WRITE_TOKEN" -H "Content-Type: application/json" \
  -d '{"root":"<專案根的絕對路徑>","docs":["docs/03_testing/contracts/TCS-<名>.md"],"approver":"<簽核人>","reason":"<核准理由>"}'
```

```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8081/sdd/fsm/<project>:freeze" -Headers @{ 'X-Bridge-Token' = $env:BRIDGE_SDD_WRITE_TOKEN } `
  -ContentType 'application/json' -Body '{"root":"<專案根的絕對路徑>","docs":["docs/03_testing/contracts/TCS-<名>.md"],"approver":"<簽核人>","reason":"<核准理由>"}'
```

### FSM 一律經 CLI 子行程（Rule 9 絕對禁令 #1）

Bridge 原始碼**不開寫 `FSM-STATE-*.yaml`**。`tests/test_sdd_integration_parity.py` 的 AST 鎖（F-4）釘住：出現 `FSM-STATE` 字串的模組不得含寫入形態呼叫、`tools.fsm_runtime` 只出現在 `app/sdd_cli.py`、每個 CLI 呼叫處只准白名單動詞常數、`spec-frozen` 只有 `:freeze` 一條路到它，且掃描器自帶故意違規的樣本證明它會紅。狀態變更一律是 `python -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime <動詞> --project <鍵> --must-exist …`：

- **固定環境**：cwd＝SDD 版本目錄；環境＝繼承 Bridge 的、**先去掉**所有 `BRIDGE_*`／`SDD_*`／`PYTHONPATH`，再設 `PYTHONPATH`、`PYTHONDONTWRITEBYTECODE=1`、`PYTHONUTF8=1`、兩個 telemetry 旗標 `0`、`SDD_STATE_DIR`（絕對路徑）、`SDD_PROJECT`；以 `procutil.popen_platform_kwargs()` 起（Windows 不閃視窗）。
- **動詞白名單**（逐動詞再有旗標白名單）：`spec-frozen`（僅經 `:freeze`）、`negotiate-enter`、`negotiate-exit --outcome agreed`（`underspecified` 一律不呼叫）、`delegate-enter [--playbook-ref run:<id>]`、`delegate-exit --decision done|failed`。越界在**送出前**就 500 `sdd_cli_usage`。
- stdout 取最後一個非空行解析單行 JSON；逾時 20 秒→終止整棵行程樹→**504 `sdd_cli_timeout`**。
- **rc→HTTP**：

| CLI rc | HTTP | reason |
|--------|------|--------|
| 0（含 `noop:true`） | 成功 | — |
| 1（非預期例外、輸出不是單行 JSON）、無法啟動 | 502 | `sdd_cli_failed` |
| 2（用法錯誤；Bridge 自己的 bug） | 500 | `sdd_cli_usage` |
| 3（前置狀態不符，帶 `current_state`） | 409 | `fsm_state_conflict` |
| 4（`invalid_argument`｜`doc_not_found`｜`doc_outside_root`｜`doc_too_large`｜`doc_not_utf8`） | 422 | `sdd_invalid_argument`（帶 CLI 的 `error` 碼） |
| 5（`state_not_found`｜`state_unreadable`） | 404／422 | `fsm_not_found`／`fsm_state_unreadable` |

- `(狀態目錄, 專案鍵)` **互斥鎖**（行程內、可重入）同時罩 CLI 呼叫與 `GET /sdd/fsm/{project}` 讀檔：讀的人不會讀到寫到一半的檔。
- 稽核兩層、以 `trace_id` 對得上：請求層 `sdd_write` 與 CLI 層 `sdd_cli`（verb、rc、結果；失敗另附 stderr 尾端；**不記**環境、權杖、`--reason` 文字）。

### 批次與 FSM 的同步（`POST /autoclaude/runs` 含 `sdd` 區塊）

`sdd` 區塊 `{spec_dir, spec_file?, fsm_project, root?, approver?}`：`root` 省略＝`execution_path`；路徑一律過 `BRIDGE_ALLOWED_PATH_ROOTS`，`spec_dir` 必須在 `root` 之下；`approver` 省略＝`console`。**建立流程**（FSM 寫入在建 run 目錄**之前**，失敗時不留半成品）：

1. 唯讀預檢（4xx、零副作用，先於取鎖）：路徑閘（`spec_file` 單獨不存在＝422 `spec_not_found`，同 compile；其餘形狀不合 422 `sanitization_failed`）→`load_spec`（凍結＝現檔；摘要不符 409 `spec_digest_changed`／`pair=frozen_vs_file`，未凍結等 422）→三點摘要（每個任務的 `spec_digest` 必須恰為現檔摘要：缺 422 `sdd_block_invalid`、不等 409 `pair=import_vs_file`）→FSM 狀態。
2. 取 advisory lock。3. FSM 寫入（依預檢表）。4. 建 run 目錄，並把 `workflow_type=aisdlc_sdd` 與 `workflow_path`（已驗證的 realpath）注入引擎 playbook（外部契約不開這兩欄）。5. spawn。6. 201（`warnings[]` 可能含 `sdd_frozen_digest_absent`：舊狀態檔或凍結時沒帶 `--digest`，只能比對「匯入時＝現檔」）。

**預檢表**（FSM 現況→依序呼叫）：`IMPLEMENTATION`→`delegate-enter`；`TEST_CONTRACT_NEGOTIATED`→`negotiate-exit agreed`＋`delegate-enter`（上次中斷的自癒）；`SPEC_FROZEN`→`negotiate-enter`＋`negotiate-exit agreed`＋`delegate-enter`（首次批次）；`AUTOCLAUDE_DELEGATED`→回收點；其他（含 `HUMAN_PENDING`、`ESCALATION`）→409 `fsm_state_conflict`；沒有狀態檔→404（Bridge 不 init）。

**回收點**（`delegate-enter` 寫下的 `playbook_ref`＝`run:<run_id>` 指向哪個 run）：缺或不以 `run:` 開頭＝外來委派→409（`detail.reason=foreign_delegation`；由人在 SDD session 解）；指向別的 FSM 專案的 run→同樣外來；查無此 run→回收（`delegate-exit done`，reason 記 `old_status=missing`）再 `delegate-enter`；指向活躍 run→409（帶 `run_id`、`run_status`）；指向終態 run→回收。回收兩步之間 `delegate-enter` 失敗＝FSM 停在 `IMPLEMENTATION`（沒有進行中的委派）、不 spawn、回 5xx，重試從常態進入。

**終態對映**（純函式 `app/sdd_sync.py::terminal_decision`；在 `handle.lock` 之外呼叫 CLI、容錯、不改 run 狀態）：`COMPLETED`→`delegate-exit done`；使用者取消（`CANCELLED`，含暫停中取消）→`done`；**引擎升級型失敗**（唯一的一型）→`delegate-exit failed`（FSM 進阻塞態 `ESCALATION`）；額度停機、引擎異常、被訊號終止、spawn 失敗、Bridge 關閉、孤兒（重啟回收）、`PAUSED`→**不動 FSM**，留給下一個批次的回收點。🔴 `done` 的語意是「委派交還控制權、未升級」，**不是「成功」**：run 成敗由後續閘門（SCG-4 審查、RTM 面板）判。spawn 失敗與建 run 目錄失敗的補償是 `delegate-exit done`（reason `SPAWN-FAILED…`，**絕不用 `failed`**）；`delegate-exit` rc 3（FSM 已被人處理）→alert `SDD_SYNC_STATE_DRIFT` 視為已就位，其他失敗→alert `SDD_FSM_SYNC_FAILED`，皆不重試。

**`:resume`／`/restore`**：重跑 `load_spec` 並比對匯入時的任務摘要（不符 409、**不 spawn**，run 仍是 `PAUSED`／終態）；FSM 為 `AUTOCLAUDE_DELEGATED` 且引用的就是本 run→直接續；為 `IMPLEMENTATION`→`delegate-enter` 重進；引用別的 run→走回收點；其餘（含 `ESCALATION`）→409。

`RunRecord.sdd`（`run.json`）：`{spec_dir, spec_file, fsm_project, root, state_dir, approver, sync}`，無任何機密；舊 `run.json` 沒有這個鍵走預設（`schema_version` 不變）。

### 規格編譯：`POST /sdd/compile`

請求另收選填 `spec_file`（相對 `spec_dir` 或絕對；須在其下、副檔名 `.md`）與 `fsm_project`（原名或淨化後的鍵；**省略＝明確不指定**，不讀 Bridge 自己的 `SDD_PROJECT`——開發機匯出它是常態）。回應另有 `spec_file`（相對 `spec_dir` 的 POSIX 路徑）、`fsm_project`（淨化後的鍵）、`frozen_digest`（`verified`｜`absent`）、`unmapped_at_ids`（規格宣告位置出現、卻沒編成步驟的 AT；**永遠出現、不是錯誤，仍回 200**，是否阻擋由消費者決定；`sdd_compile` CLI 對同樣情形是 rc 6 fail-closed，這個不對稱是刻意的）、`spec_format_version`、`warnings[]`（專案根是 git 工作樹而 `build/reports/fsm` 沒被忽略時有 `state_dir_not_ignored`）。例外對映：`SpecDigestMismatchError`→409 `spec_digest_changed`（`pair=frozen_vs_file`；先於其父類）、`SpecNotFrozenError`→422 `spec_not_frozen`、`SpecTaintedError`→422 `spec_tainted`、`SpecFormatVersionError`→422 `spec_format_version_unsupported`、`FileNotFoundError`→422 `spec_not_found`、`ValueError`→422 `spec_ambiguous`。選檔以**專案鍵**為準（同目錄多專案共處只認指定者、未指認即 fail-closed、找不到也不往上層目錄找）。

### 專案名規則（S-10）與 URL 定址邊界

進入 Bridge 的專案名（body 的 `fsm_project`、`sdd.fsm_project`、路徑參數）一律先過 `app/fsm_names.py::fsm_component`，所以傳原名與傳淨化後的鍵等價。它是 `AISDLC_SDD/scripts/component_sanitizer.py::sanitize_component` 的**逐字鏡像**（不 import；`tests/test_fsm_names.py` 以依路徑載入 SDD 原檔逐樣本對拍，SDD 改規則時對拍先紅）：NFC 正規化＋`strip()`→把 Windows 禁用字元 `< > : " | ? * \`、`/`、控制字元（< 0x20）與 DEL 換成 `_`→截到 80 字→`rstrip(" .")`（吃光退成 `untitled`；`..`／`.` 因此不會留下穿越 token）→若 stem（第一個 `.` 之前、去尾端空白）是 Windows 保留裝置名（`CON PRN AUX NUL COM0-9 LPT0-9 CONIN$ CONOUT$ COM¹²³ LPT¹²³`，不分大小寫）加 `_` 前綴並重截。`is_fsm_project_name` 是 Bridge 自己的**輸出域判準**（不是鏡像；用在磁碟上的檔名片段，`GET /sdd/fsm` 清單）：非空、已是 NFC、≤ 80 字、不含上述禁用字元、不以空白開頭、不以 `.` 或 ASCII 空白結尾（與 ADR 字面「無前後空白」有一處刻意差異：尾端判準取 `rstrip(" .")` 的不動點，否則 sanitizer 截斷後以全形空白結尾的輸出會被它自己的判準拒掉）。

🔴 **URL 定址邊界（D-115-18 ②）**：路徑參數 `{project}` 只收淨化後的 FSM 鍵（不改成 `{project:path}`）；原名含 `/` 的專案（`x/y`→檔名 `x_y`）**無法由 URL 定址**（兩段路徑或 `%2F` 都是 404），改用清單與每個回應都帶的 `fsm_project`（＝鍵）。請求本文裡的專案名（compile、`sdd` 區塊）不受此限，會被淨化成同一個鍵。已知上游邊界（回報主控）：`sanitize_component` 在截斷到 80 字後若以 Unicode 空白結尾，再淨化一次會被開頭的 `strip()` 吃掉而不冪等；Bridge 鏡像與它逐字相同，現況由 `test_known_upstream_corner_…` 釘住。

## 追蹤碼與日誌（契約 v1.2 §3.1.1；NFR-9.4-04）

console-api 對 Bridge 的**每個請求**都帶標頭 `X-Trace-Id`（UUID）。Bridge 的 HTTP 中介層（`app/tracing.py`，純 ASGI、包在最外層，所以 SSE 串流與 500 的回應也一樣）：

1. 讀取該標頭；**缺漏或格式不合**（1～64 個字元、只含英數與 `.`、`_`、`-`、首字元為英數；值會原樣進日誌，空白與控制字元一律拒收）時自產 uuid4；
2. **回應回帶同名標頭**；
3. 把值放進 `contextvars`，**每一行**日誌都帶 `trace_id=<值>`（`app/logsetup.py`）。沒有請求上下文的行（啟動、關閉、與請求無關的背景執行緒）是 `trace_id=-`；run 的監督執行緒沿用「觸發那次 spawn 的請求」的值。

日誌格式（stderr 與 `BRIDGE_LOG_DIR/bridge.log` 相同）：`<UTC 時間>Z <等級> [<logger>] trace_id=<值> <訊息>`，一筆日誌恆為一行（訊息與 traceback 內的換行寫成字面 `\n`）；uvicorn 的啟動與存取日誌同格式（`POST /autoclaude/runs HTTP/1.1" 201` 那一行帶發起請求的 trace_id）。範例：

```
2026-10-15T16:57:01.132Z INFO  [uvicorn.access] trace_id=96c90695-e4fe-480b-8eb4-3e457de0aed6 172.17.0.1:38270 - "GET /health HTTP/1.1" 200
```

```bash
grep 'trace_id=<值>' "$BRIDGE_LOG_DIR/bridge.log"               # 本機設了 BRIDGE_LOG_DIR 時
(cd AgentConsole && docker compose logs engine-bridge | grep 'trace_id=<值>')    # Docker 全棧
```

```powershell
Select-String -Path "$env:BRIDGE_LOG_DIR\bridge.log" -Pattern 'trace_id=<值>'
Push-Location AgentConsole; docker compose logs engine-bridge | Select-String 'trace_id=<值>'; Pop-Location
```

## E2E 不靠真 Claude：`aisdlc-mock-claude`

AutoClaude 的 `claude.command` 是**單一字串、不做 shlex 切分**，且 Kernel 路徑只呼叫 `<command> … -p <prompt>`（`PlaybookTask.command` 欄位零消費），
所以 `python -u dummy_cli.py` 這種寫法**行不通**（實測：引擎直接 FileNotFoundError）。本套件改安裝一個真正的可執行檔：
POSIX 根層 `.venv/bin/aisdlc-mock-claude`、Windows 根層 `.venv\Scripts\aisdlc-mock-claude.exe`（Docker 映像內在 PATH 上）。

```json
{"run_id":"<uuid>","project":"demo","execution_path":"<允許根目錄下的絕對路徑>",
 "playbook":{"project":"demo","tasks":[{"step_id":"T01","name":"一","prompt":"請輸出 [ONE_DONE]","expected_output_regex":"\\[ONE_DONE\\]"}]},
 "config_overrides":{"claude":{"command":"aisdlc-mock-claude"},"token_guard":{"auto_resume":false}},
 "env":{"MOCK_CLAUDE_DELAY":"0.5"}}
```

替身回放 prompt 內所有 `[KEYWORD]`；旋鈕（皆走請求的 `env`）：`MOCK_CLAUDE_DELAY`（每次呼叫秒數，預設 0.2）、`MOCK_CLAUDE_TRACE`（把每次呼叫 append 成 JSONL）、
`MOCK_CLAUDE_FAIL_REGEX`（prompt 命中時不輸出關鍵字＝讓 evaluator 判失敗）、`MOCK_CLAUDE_IGNORE_TERM=1`（POSIX：忽略 SIGTERM，用來驗強殺升級）。
Brain（MiniMax）的 mock 用 `AutoClaude/tools/mock_brain_server.py --port 9100`（它**不支援**拆解決策；拆解測試用 FakeBrain，見 `tests/test_decompose.py`）。

## 測試

```bash
cd AgentConsole/engine-bridge && . ../../.venv/bin/activate
ruff check .
python -m pytest -q                 # 序列；測試各用獨立工作區與臨時埠，亦可 -n auto 平行
```

```powershell
Push-Location AgentConsole\engine-bridge; ..\..\.venv\Scripts\Activate.ps1; ruff check .; python -m pytest -q; Pop-Location
```

不需 DB、不需真 Claude：真引擎（`python -m autoclaude`）＋ mock claude，經真 HTTP／SSE（背景執行緒起 uvicorn）。
W7 新增兩支：`tests/test_resources.py`（`resources` 取樣：欄位型別與範圍、整機正規化、終態與 PAUSED 為 null、已消失的 pid 不炸、**跨 tick 持有同一組 `Process` 物件**、過期樣本回 null、背景執行緒與 spawn 後立即補樣，含真 psutil 行程與經真 HTTP 的 E2E）、`tests/test_sdd_fsm.py`（`GET /sdd/fsm` 清單與 `errors`、detail 的 `human_pending`／`retry_history`／`rtm_coverage`；用合成夾具，另有一支對**真實**狀態檔的測試，該版本沒有任何狀態檔時 skip 並寫明原因）。
整合輪 115（ADR-XPLAT-016）新增：`tests/fake_sdd.py`（假 SDD 樹：一支只依 ADR §4 契約回放 JSON 的迷你 FSM 狀態機 CLI，記錄 argv／cwd／環境到 `fake_calls.jsonl`）與 `tests/sdd_run_support.py`（共用夾具）；`test_fsm_names.py`（專案名鏡像與 SDD 原檔逐樣本對拍）、`test_spec_digest.py`、`test_sdd_cli.py`（argv／環境／rc 對映／逾時殺樹／白名單／互斥鎖）、`test_sdd_sync.py`（reason 組字、終態對映表、預檢表、回收點判定）、`test_sdd_token.py`、`test_sdd_freeze.py`（`:freeze` 逐格）、`test_sdd.py`（compile 擴充）、`test_sdd_run.py`（建立流程、預檢、補償、稽核）、`test_sdd_run_lifecycle.py`（終態同步、回收點、`resume`／`restore` 重驗與權杖、孤兒、`RunRecord`、`_child_env`）、`test_rtm.py`、`test_sdd_integration_parity.py`（跨專案對拍 F-1～F-11：compile 與 `sdd_compile` CLI 逐任務相等、只認指定者、凍結後改檔、AST 鎖、摘要演算法、權杖與環境不外洩、同步與補償矩陣、AT 文法；**含用真 SDD CLI 子行程的整合測試**——真 CLI 在該環境 import 不了時略過並印原因）。F-8 在 `test_fsm_names.py`、F-12 在 `test_sdd_cli.py`；F-5（`phase` 表對 SDD LATEST 狀態集合的對拍，用真 SDD 樹的子行程取 `_HAPPY_PATH`／`OBSERVATION_STATES`／`_BLOCKING_STATES`）已真跑。`test_fsm_phase.py` 收納 W4 dogfood 的七個 AT（真 claude haiku 寫出、SCG-4 審查通過，測試名保留 AT 編號）與契約 §3.1.5 的逐鍵對映表。
另有兩支與 Docker 部署相關的測試：`tests/test_health_deep.py`（`/health/deep` 的 200／503 與各項檢查的失敗路徑；`sdd` 的未設／有效／全新 clone／不存在／是檔案／空目錄六種情境，並鎖住「`sdd.ok` 為 false 時整體仍 200、頂層 `reason` 不含 sdd」）、`tests/test_trace_logging.py`（`X-Trace-Id` 回帶、每行日誌的 `trace_id`、`BRIDGE_LOG_DIR`）；以及 `tests/test_deploy_config.py`——**靜態**讀檔，把 W5 的部署缺陷修法（映像裝 git、healthcheck 打 `/health/deep`、compose 必填金鑰、日誌卷 `nocopy`、信任代理預設值、nginx `error_log crit`、`restore.sh` 的 root 階段建目錄…）各釘成一條斷言，因為這類缺陷只在 Docker 全棧真跑才現形，而 docker／nginx 設定沒有自己的 pytest 家。
DB 整合測試（寫入 `console` schema、advisory lock 跨實例互斥）需要一個可寫的 PostgreSQL：

```bash
docker run -d --rm --name bridge-test-pg -e POSTGRES_PASSWORD=<YOUR_PASSWORD> -p 55432:5432 pgvector/pgvector:pg18
BRIDGE_TEST_DSN='postgresql://postgres:<YOUR_PASSWORD>@127.0.0.1:55432/postgres' python -m pytest tests/test_db_integration.py -q
docker stop bridge-test-pg          # 做完要收
```

```powershell
docker run -d --rm --name bridge-test-pg -e POSTGRES_PASSWORD=<YOUR_PASSWORD> -p 55432:5432 pgvector/pgvector:pg18
$env:BRIDGE_TEST_DSN = "postgresql://postgres:<YOUR_PASSWORD>@127.0.0.1:55432/postgres"; python -m pytest tests/test_db_integration.py -q
docker stop bridge-test-pg
```

## Docker

build context 必須是 **monorepo 根**（要 COPY 兄弟目錄 `AutoClaude/`）；進 context 的檔案由 `Dockerfile.dockerignore` 限定（約 4 MB）。

```bash
docker build -f AgentConsole/engine-bridge/Dockerfile -t aisdlc-engine-bridge:dev .
docker run --rm -p 8081:8081 aisdlc-engine-bridge:dev        # 另一個終端機：curl -s localhost:8081/health
```

```powershell
docker build -f AgentConsole/engine-bridge/Dockerfile -t aisdlc-engine-bridge:dev .
docker run --rm -p 8081:8081 aisdlc-engine-bridge:dev        # 另一個終端機：Invoke-RestMethod http://localhost:8081/health
```

映像為非 root（uid 10001）、`ENGINE_WORKSPACE=/workspace`（VOLUME）、有 HEALTHCHECK（打 `/health/deep`）。映像安裝 **`git` 與 `ca-certificates`**（`apt-get install --no-install-recommends`，build 時以 `RUN git --version` 冒煙）：引擎內共 11 處 subprocess 呼叫 git，`python:3.11-slim` 沒有它——QA DEF-AC-003（P1）曾使 Docker 全棧下任何批次一律 `FAILED`。`/app/logs` 預設存在、權限 `1777`：compose 把 `app_logs` 卷掛在這裡讓 `BRIDGE_LOG_DIR=/app/logs`，backend 以另一個 uid（1001）寫同一個卷；具名卷還空著時 Docker 會把「最後 create 的容器」映像內該目錄的擁有者與權限複製進卷根，所以 compose 讓 backend 以 `:nocopy` 掛載，卷根只由本映像的 `1777` 決定（細節：`docker/README.md`〈9〉#32）。**映像不含 `claude` CLI 與 AISDLC_SDD**：
全棧 Docker 的 E2E 用內建替身（`claude.command=aisdlc-mock-claude`）；`/sdd/*` 需由 compose 以唯讀 volume 掛入 `AISDLC_SDD`（整個或單一版本目錄）並設 `SDD_ROOT`；FSM 狀態檔寫在**專案根**的 `build/reports/fsm`（`BRIDGE_ALLOWED_PATH_ROOTS` 之下、可寫），不寫進唯讀的 SDD 樹；
SDD 寫入面預設停用（compose 的 `BRIDGE_SDD_WRITE_TOKEN` 預設空；啟用方式見 `.env.example`）。
要跑真 Claude 請用本機模式。基底映像可用 `--build-arg PYTHON_IMAGE=…` 覆寫；但建置時的 `apt-get`（裝 git）需要連到 Debian 套件庫，所以不再能在完全離線的機器上建置。

## 設計重點（皆為對真引擎的實證，不是假設）

- **引擎不寫步驟級 checkpoint**：只有 token HALT／ESC+F12 中斷／演化才寫，且整份跑完會清掉。所以 Bridge 在「推得步驟 k 完成」時自己記**歷史快照**
  （`GET /checkpoints`、restore 的來源）；續跑前用**引擎自己的** `FileStateRepository` 把快照寫成它的 checkpoint（含 checksum），再**不帶 `--fresh`** 重啟，由引擎的
  `_resolve_start` 從 `step_idx` 接續。
- **步驟事件**取自引擎 stdout 的三種訊號（`subprocess 模式啟動：…`、`=== STEP_TOKEN_PEAK | step=… ===`、`Playbook 結束 | KernelResult(…)`），解析器在 `app/logparse.py`；
  格式漂移時退化成只發 `log` 事件，且在 COMPLETED 時以引擎結果校正計數並發 `STEP_TRACKING_GAP` alert。
- **pause**＝在「下一個步驟的啟動行」出現的瞬間（步驟 k 已完成）終止引擎**整棵行程樹**（引擎把 claude 放在自己的 session，只殺引擎會留下孤兒）；剛 spawn 的下一步會被一併終止、續跑時由引擎重做。
  一次續跑至少前進一步才允許再暫停（不會 pause／resume 空轉）；暫停請求來不及（已在最後一步）則 run 照常 COMPLETED。
- **stop**＝終止整棵樹，逾 `BRIDGE_STOP_GRACE_SECONDS` 仍活著的升級強殺並發 `FORCE_KILL` alert；PAUSED 狀態下 stop 直接收尾。
- **鎖**：`project:execution_path`（路徑 normcase＋NFC）；PAUSED 期間**持鎖**（resume、restore 都不重搶；同一個 run 對同一把鎖重取＝冪等，不新開連線），終態釋放（終態 run 的 restore 才重取，可能 409；重取後、spawn 前失敗會立刻放掉，終態 run 不留鎖，PAUSED run 失敗仍持鎖）；DB 模式再加 `pg_try_advisory_lock(hashtext(key))`（每把鎖一條專用連線）。
- **孤兒回收**（啟動時）：RUNNING／PAUSING／INITIALIZING 且 PID 不存活 → `FAILED`（reason 含 `orphaned`）、CANCELLING → `CANCELLED`、釋放鎖；PID 仍存活且身分（create_time）相符 → 先終止再標記；**身分對不上的 PID 絕不終止**；PAUSED 重新登記鎖。
- **機密不落盤**：`config_overrides` 拒絕 `api_key`／`db_dsn`（走 `env`）；`run.json` 只記 env 的**名稱**；Bridge 重啟後遺失的請求層 env 會發 `ENV_LOST` alert，可在 `:resume`／`restore` 的 body 帶 `env` 重新提供。
- **引擎狀態不污染專案目錄**：`checkpoint_dir`／`log_dir` 等一律在 run 工作區，`storage` 固定 `yaml_only`。
- 資料落地：`<ENGINE_WORKSPACE>/<run_id>/{run.json,events.jsonl,playbook.yaml,config.yaml,engine-N.log,history/,engine/{checkpoints,logs}}`；`_audit.jsonl`（審計）、`_drafts/`（拆解草稿）。

## 已知限制

- run 登記表與事件環常駐記憶體（單機量級足夠；事件另存 JSONL，重啟後可重播）。
- 不處理 Claude Code 的授權提示互動（引擎自己的 `loop.auth_patterns` 負責）。
- `/sdd/compile` 與批次預檢底層的 adapter 自整合輪 115 起**以專案鍵選 FSM 狀態檔**（`fsm_project`；同目錄多專案共處又沒給鍵即 fail-closed，不再取字母序第一份）；Bridge 一律顯式傳值（含空字串＝明確不指定），不讀自己的環境。
- 路徑參數無法定址原名含 `/` 的專案（見〈專案名規則與 URL 定址邊界〉）。
- SDD 寫入面只由 `BRIDGE_SDD_WRITE_TOKEN` 這一道 HTTP 權杖封住；它不防禦主動對抗的 AI（引擎子行程內的步驟仍可自己執行框架的 FSM CLI，見〈SDD 整合〉的誠實劃界）。
- 終態同步在終態事件之後約 0.1～0.5 秒才完成（CLI 最壞 20 秒，不該卡住 `snapshot()`）：這段視窗內 run 已是終態、FSM 仍在 `AUTOCLAUDE_DELEGATED`，由下一次建立的回收點與 `GET /sdd/fsm` 的現況為準。

## Windows 注意

程式碼已按 Windows 語意撰寫（`proc.terminate()`／`kill()`、`psutil.pid_exists`、`CREATE_NEW_PROCESS_GROUP`、路徑 normcase、`replace` 包 `try/except OSError`，並有 AST 測試禁用 POSIX-only API），
但**尚未在 Windows 實機驗證**；驗證清單見交卷報告〈Windows 接續注意〉。
