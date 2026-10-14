# Engine Bridge（FastAPI 旁車）

把兩個**純 CLI** 引擎（`AutoClaude/`、`AISDLC_SDD/`）包成 REST + SSE，給 Spring Boot 後端呼叫（PRD §0.2）。
單一服務、單一埠 `8081`，以路徑前綴區分：`/autoclaude/*`、`/sdd/*`、`/health`。**零侵入**：不改 `AutoClaude/`、`AISDLC_SDD/` 任何檔。

```
app/main.py        FastAPI app／lifespan（啟動做孤兒回收）／/health
app/settings.py    環境變數 → Settings        app/models.py    請求／回應模型（照 API 契約）
app/security.py    NFR-SEC-03/04 消毒鏈       app/runner.py    spawn `python -m autoclaude`、監督、pause/resume/stop/restore
app/events.py      events.jsonl + 記憶體環    app/logparse.py  引擎 stdout 步驟訊號解析 + 步驟狀態機
app/checkpoints.py 歷史快照 + 引擎格式寫入    app/locks.py     並發互斥（行程內 + PG advisory lock）
app/db.py          DB 模式狀態鏡射            app/decompose.py 目標拆解（GoalDecomposer）+ 草稿存檔
app/procutil.py    行程樹治理（psutil）       app/mock_claude.py E2E 用的確定性 claude 替身（console script）
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
| `BRIDGE_TEST_DSN` | （測試用） | 設了才跑 `tests/test_db_integration.py` |

## API（契約逐字；補充與落地差異見 `AgentConsole/docs/02_architecture/Architecture.md` §10）

`POST /autoclaude/runs`（201／409 `advisory_lock_held`＋`holder_run_id`／422）、`POST /autoclaude/runs/{id}:pause|:resume|:stop`（202）、
`GET /autoclaude/runs/{id}`、`GET …/stream?after=`（SSE，亦認 `Last-Event-ID`）、`GET …/events?after=&limit=`、`GET …/checkpoints`、`POST …/restore`、
`POST /autoclaude/decompose`、`POST /autoclaude/decompose/{draft_id}:approve`、`GET /sdd/version`、`GET /sdd/fsm/{project}`、`POST /sdd/compile`。
錯誤封包一律 `{"code":<狀態>,"reason":"…",…}`；422 另帶 `violations`（逐項列出違規欄位與字元）。互動式文件：`http://localhost:8081/docs`。

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

映像為非 root（uid 10001）、`ENGINE_WORKSPACE=/workspace`（VOLUME）、有 HEALTHCHECK。**映像不含 `claude` CLI 與 AISDLC_SDD**：
全棧 Docker 的 E2E 用內建替身（`claude.command=aisdlc-mock-claude`）；`/sdd/*` 需由 compose 以唯讀 volume 掛入 `AISDLC_SDD`（整個或單一版本目錄）並設 `SDD_ROOT`；
要跑真 Claude 請用本機模式。基底映像可用 `--build-arg PYTHON_IMAGE=…` 覆寫（離線機器用快取映像驗建置步驟）。

## 設計重點（皆為對真引擎的實證，不是假設）

- **引擎不寫步驟級 checkpoint**：只有 token HALT／ESC+F12 中斷／演化才寫，且整份跑完會清掉。所以 Bridge 在「推得步驟 k 完成」時自己記**歷史快照**
  （`GET /checkpoints`、restore 的來源）；續跑前用**引擎自己的** `FileStateRepository` 把快照寫成它的 checkpoint（含 checksum），再**不帶 `--fresh`** 重啟，由引擎的
  `_resolve_start` 從 `step_idx` 接續。
- **步驟事件**取自引擎 stdout 的三種訊號（`subprocess 模式啟動：…`、`=== STEP_TOKEN_PEAK | step=… ===`、`Playbook 結束 | KernelResult(…)`），解析器在 `app/logparse.py`；
  格式漂移時退化成只發 `log` 事件，且在 COMPLETED 時以引擎結果校正計數並發 `STEP_TRACKING_GAP` alert。
- **pause**＝在「下一個步驟的啟動行」出現的瞬間（步驟 k 已完成）終止引擎**整棵行程樹**（引擎把 claude 放在自己的 session，只殺引擎會留下孤兒）；剛 spawn 的下一步會被一併終止、續跑時由引擎重做。
  一次續跑至少前進一步才允許再暫停（不會 pause／resume 空轉）；暫停請求來不及（已在最後一步）則 run 照常 COMPLETED。
- **stop**＝終止整棵樹，逾 `BRIDGE_STOP_GRACE_SECONDS` 仍活著的升級強殺並發 `FORCE_KILL` alert；PAUSED 狀態下 stop 直接收尾。
- **鎖**：`project:execution_path`（路徑 normcase＋NFC）；PAUSED 期間**持鎖**（resume 不用重搶），終態釋放；DB 模式再加 `pg_try_advisory_lock(hashtext(key))`（每把鎖一條專用連線）。
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
