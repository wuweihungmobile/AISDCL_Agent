# Engine Bridge（FastAPI 旁車）

把兩個**純 CLI** 引擎（`AutoClaude/`、`AISDLC_SDD/`）包成 REST + SSE，給 Spring Boot 後端呼叫（PRD §0.2）。
單一服務、單一埠 `8081`，以路徑前綴區分：`/autoclaude/*`、`/sdd/*`、`/health`、`/health/deep`。**零侵入**：不改 `AutoClaude/`、`AISDLC_SDD/` 任何檔。

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
| `BRIDGE_LOG_DIR` | （未設＝不寫檔） | 有值時，日誌另寫成滾動檔 `<dir>/bridge.log`（UTC 午夜切檔、保留 7 份）；stderr 的日誌照舊。目錄建不出來或不可寫只在 stderr 留一則警告，Bridge 照常啟動。docker compose 設 `/app/logs`（與 backend 共用 `app_logs` 卷）。見〈追蹤碼與日誌〉 |
| `BRIDGE_TEST_DSN` | （測試用） | 設了才跑 `tests/test_db_integration.py` |

## API（契約逐字；補充與落地差異見 `AgentConsole/docs/02_architecture/Architecture.md` §10）

`POST /autoclaude/runs`（201／409 `advisory_lock_held`＋`holder_run_id`／422）、`POST /autoclaude/runs/{id}:pause|:resume|:stop`（202）、
`GET /autoclaude/runs/{id}`、`GET …/stream?after=`（SSE，亦認 `Last-Event-ID`）、`GET …/events?after=&limit=`、`GET …/checkpoints`、`POST …/restore`、
`POST /autoclaude/decompose`、`POST /autoclaude/decompose/{draft_id}:approve`、`GET /sdd/version`、`GET /sdd/fsm`、`GET /sdd/fsm/{project}`、`POST /sdd/compile`、`GET /health`、`GET /health/deep`。
錯誤封包一律 `{"code":<狀態>,"reason":"…",…}`；422 另帶 `violations`（逐項列出違規欄位與字元）。互動式文件：`http://localhost:8081/docs`。

### 資源取樣：`GET /autoclaude/runs/{id}` 的 `resources`（契約 v1.3 §3.1.2；W7 D-12）

回應多一個欄位 `resources`：`{"cpu_percent": 12.3, "rss_bytes": 104857600, "process_count": 3, "sampled_at": "2026-10-16T04:30:05.123456+00:00"}`，或 `null`。

- `cpu_percent`＝**整機正規化**：引擎行程樹（`python -m autoclaude` 與它的全部子孫，含 claude 或 mock claude；不含 Bridge 自己、也不含別的 run）各行程 `cpu_percent` 的總和 ÷ 邏輯核心數，夾在 0.0～100.0、小數 1 位（100＝整台機器所有邏輯核心被占滿，與 `top` 的單核 100% 不同）。`rss_bytes`＝各行程 RSS 的總和（共用頁會重複計入，是上界估計）。`process_count`＝取樣成功的行程數（含根）。`sampled_at` 帶 offset（Bridge 一律 UTC）。**不含** pid、命令列、環境變數。
- 何時是 `null`：引擎行程樹不存活（尚未 spawn、**PAUSED**、任何終態、行程已消失）、還沒有第一筆樣本、或最近一筆超過 **15 秒**沒更新（取樣器卡住時寧可回 null，也不回過期的數字）。resume／restore 後根 pid 換了，舊樣本不會被沿用。
- 怎麼取樣：`app/resources.py` 的背景執行緒（lifespan 在孤兒回收後啟動、關閉時先停）**每 5 秒**對每個存活的 run 取一筆，只留最近一筆；請求路徑只讀那一筆，**從不取樣、不阻塞**。新 spawn 的 run 會喚醒執行緒立刻補一筆（CPU 為 0.0：沒有上一次的基準）。
- 🔴 陷阱：`psutil.Process.cpu_percent(interval=None)` 是「與同一個 Process 物件上一次呼叫之間」的差值，而 `children()` 每次都回新物件——所以取樣器**跨 tick 持有每個 pid 的 `Process` 物件**（以 pid＋create_time 判斷是不是同一個行程），每個 tick 重建物件會讓 CPU 永遠是 0.0。
- 單一行程取不到（剛結束、權限不足）只略過它；取樣器自己的例外只記日誌（同處最多每 60 秒一行，且只記例外類別）。Windows 行為＝只走 psutil；用 venv 的 `python.exe` 啟動的行程會多一層啟動器殼，`process_count` 因此比直覺大。

### SDD 狀態：`GET /sdd/fsm`（清單）與 `GET /sdd/fsm/{project}`（W7 D-16）

資料來源是 `<SDD_ROOT>/build/reports/fsm/FSM-STATE-<project>.yaml`（`project` 只收 `^[A-Za-z0-9._-]{1,128}$`）。`SDD_ROOT` 無效（沒設、不是目錄）一律 `503 sdd_unavailable`。

- `GET /sdd/fsm` → `{"root":"AISDLC_SDD_v0.30","projects":[{"project","source","current_state","updated_at"}],"errors":["…"]}`。`project`＝檔名去掉 `FSM-STATE-` 與 `.yaml`（就是 `GET /sdd/fsm/{project}` 吃的那個鍵）；依 `project` 不分大小寫排序；名稱不合白名單、讀不動（非 UTF-8、不是 YAML、巢狀過深）、缺 `fsm_state` 根節點、或 symlink 指到 `fsm` 目錄之外的檔名放進 `errors`，不影響其他檔。`build/reports/fsm` 不存在（全新 clone 沒有，原因見上方 `/health/deep` 第五項的說明）回 **200 空清單**，不是錯。
- `GET /sdd/fsm/{project}`：既有 8 個欄位不動，另增（只增不減）：
  - `human_pending` ＝ `{"count": N, "items": [尾 5 筆，原樣]}`，來源 `human_pending_tracking`。**真實檔裡它是單一 dict**（`entered_at`、`reminder_sent_at`、`reminder_hours`、`escalation_hours`；離開 HUMAN_PENDING 時 `entered_at` 被清成 null）：`entered_at` 有值＝正在等人（`count` 1、`items` 為該 dict 原樣），沒有＝`count` 0、`items` 空；若哪天改成 list，則 `count`＝筆數、`items`＝尾 5 筆。
  - `retry_history` ＝ `{"count": N, "last": 尾 1 筆｜null}`。**真實檔裡它是 dict of dict**，以重試閘為鍵（`SCG_VALIDATION`、`PR_REVIEW`、`RTM_VERIFY`），每個閘有 `current_count`、`max_limit`、`history`（list，每筆 `attempt`、`date`、`failure_reason`、`scg_gate`）：`count`＝各閘 `history` 筆數的總和，`last`＝全部筆中 `date` 最晚者（同時刻取後出現的）原樣再加一個 `gate` 欄；若改成 list，則取筆數與尾端一筆。
  - `rtm_coverage` ＝ 檔內 `fsm_state.rtm_coverage` 原樣，沒有這個鍵就是 `null`（真實狀態檔沒有任何 RTM 覆蓋數值，所以目前恆為 `null`）。
- 找不到檔、`project` 不合白名單 → 404 `fsm_not_found`；檔存在但讀不動 → 422 `fsm_state_unreadable`。

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
全棧 Docker 的 E2E 用內建替身（`claude.command=aisdlc-mock-claude`）；`/sdd/*` 需由 compose 以唯讀 volume 掛入 `AISDLC_SDD`（整個或單一版本目錄）並設 `SDD_ROOT`；
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
- `/sdd/compile` 底層 adapter 向上找 FSM 狀態檔時取字母序第一個 `FSM-STATE-*.yaml`（與 project 無關）——這是 AutoClaude 既有行為，Bridge 未更動。

## Windows 注意

程式碼已按 Windows 語意撰寫（`proc.terminate()`／`kill()`、`psutil.pid_exists`、`CREATE_NEW_PROCESS_GROUP`、路徑 normcase、`replace` 包 `try/except OSError`，並有 AST 測試禁用 POSIX-only API），
但**尚未在 Windows 實機驗證**；驗證清單見交卷報告〈Windows 接續注意〉。
