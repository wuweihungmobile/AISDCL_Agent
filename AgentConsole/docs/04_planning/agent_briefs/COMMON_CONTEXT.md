# 共同背景（每位 agent 都必須先讀完本檔）

## 🔴 本輪環境覆寫（Windows 輪，2026-10-15 起；與下文衝突處以本節為準）
- monorepo 根：`D:\CursorProject\AISDCL_Agent`（Windows 11；**只有 PowerShell 7 工具，Bash 工具被 hook 停用**）。所有指令用 PowerShell 形態：不准裸 `cd`／`Set-Location`，換目錄用 `Push-Location <絕對路徑>; …; Pop-Location` 在**同一次呼叫**成對；不准 `VAR=value cmd` 前綴，改 `$env:VAR="value"; cmd`；讀 rc 不接管線——先把輸出導到檔案再讀 `$LASTEXITCODE`，要看內容用 `Get-Content <log> -Tail N`。
- 工具鏈（主控已在本機親驗）：Python＝根層 `.venv`，一律寫完整路徑 `D:\CursorProject\AISDCL_Agent\.venv\Scripts\python.exe`（Bridge 已裝進去；`aisdlc-mock-claude.exe` 與 `uvicorn.exe` 在 `.venv\Scripts\`）；Java 21（`java -version`＝21.0.10）＋ `.\gradlew.bat`（`clean build` 已 BUILD SUCCESSFUL）；Node 22.23.3（nvm-windows；`node --version` 必須印 v22，不是就停下回報）；Docker Desktop 在線；`uv` 在 PATH。
- 暫存目錄：`C:\Users\wuwei\AppData\Local\Temp\claude\D--CursorProject-AISDCL-Agent\6121f0db-8785-4286-9143-5c37c2fc9496\scratchpad\<你的角色>\`（自己 `New-Item -ItemType Directory -Force`）。下文第 8 條的 macOS 暫存路徑與「你在哪裡」的 macOS 路徑**作廢**。
- 長輸出一律導檔再看尾端：`<cmd> > "<scratchpad>\x.log" 2>&1; $rc = $LASTEXITCODE; "rc=$rc"; Get-Content "<scratchpad>\x.log" -Tail 40`。
- 背景服務（PG 容器／backend／Bridge／frontend dev）用 `run_in_background: true` 啟動，交卷前自己關掉（`Stop-Process -Id`／`docker rm -f`），不留孤兒；交卷附 `Get-Process java,node,python -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,StartTime` 的輸出。
- Windows 既有事實：Bridge 的 `BRIDGE_ALLOWED_PATH_ROOTS` 以 `;` 分隔；路徑比對 normcase；`terminate()` 是強殺（Architecture L-5）；venv 的 `python.exe` 是啟動器，會再 spawn 真正的直譯器（行程樹多一層，Bridge 測試已處理）；Windows 整條命令列上限 32,767 字元（Architecture L-9，prompt ≤ 20,000 字元）。
- 不准改：`AutoClaude/`、`AISDLC_SDD/`、根層 `CLAUDE.md`、`.claude/`、`tools/`、`.github/`、根層 `ONBOARDING.md`、`AutoClaude/.perf_baseline.toml`。

## 你在哪裡
- monorepo 根：`/Users/wuweihong/Antigravity/AISDCL_Agent`（macOS，zsh，Python 3.11 + uv，Java 21（Homebrew openjdk@21），Node 22.23.3 + npm 10.9（已在 PATH），Docker 29.6 已在跑）。
- 既有兩個子專案（**一個位元組都不准改**）：
  - `AutoClaude/`：Python 微核心 Playbook 引擎。CLI 入口 `python -m autoclaude <playbook.yaml> [--config config.yaml] [--fresh]`；無 HTTP server。
  - `AISDLC_SDD/`：規格先行框架，LATEST 版＝`AISDLC_SDD/AISDLC_SDD_v0.30/`（其他版本是凍結快照）。
- 本輪要新建第三個子專案 **`AgentConsole/`**（monorepo 根下，與上面兩個同層）。它是 PRD 描述的「AISDLC Agent Console UI」。

## 唯一真相源（先讀，再動手）
1. **PRD**：`docs/01_requirements/Agent_ConsoleUI_PRD.md`（3,576 行）。§0 是權威校正區（凌駕後文）。你負責的範圍對應哪些章節，任務書會指名。
2. **UI 設計稿（像素級定稿）**：`docs/01_requirements/01.UI_Design/Design_ConsoleUI/README.md`（九個畫面、設計 token、互動行為），`_ds/.../tokens/*.css`（顏色／字體／間距／圓角 token），`screenshots/*.png`（九張整頁截圖），`Agent Console.dc.html`（可在瀏覽器開的互動原型，**不可直接移植**）。
3. **架構圖**（Architect 產出後才有）：`AgentConsole/docs/02_architecture/Architecture.md` 與 `ADR-001-TechStack-Lock.md`。

## 掌舵者（主控 Fable）已拍板的決策（不要重新討論，照做）
- **目錄**：`AgentConsole/{frontend,backend,engine-bridge,docker,docs}` + `docker-compose.yml` + `.env.example` + `CLAUDE.md` + `README.md`。PRD §11.8 的 `project-root/` 就是 `AgentConsole/`。
- **技術棧鎖定**：
  - 前端：Next.js **16.x**（npm 現查 latest 16.4.0）+ TypeScript 5 strict + Tailwind CSS **4** + shadcn/ui + lucide-react。圖表：先 spike Tremor Raw（Tailwind 4 相容版）；30 分鐘內搞不定就改用 shadcn `chart` 元件（Recharts 底層），把結果寫進 ADR。
  - 後端：Spring Boot **4.1.x**（start.spring.io 現查預設 4.1.1；Spring Boot 3.x OSS 已 EOL，PRD §3 版本註記授權「鎖定時取當時 stable、≥3.3」）+ Java 21 + Gradle Kotlin DSL + Clean Architecture 四層（PRD §4.1 套件結構）+ Spring Data JPA + Flyway + SpringDoc OpenAPI + Spring Security JWT。
  - Engine Bridge：Python 3.11 + FastAPI + uvicorn + psycopg 3；🔴 **改裝進根層 `.venv`**（原「自己的 venv」被 repo 單一 venv 規則的 pre-commit 閘否決，2026-10-15）：`VIRTUAL_ENV=<repo>/.venv uv pip install -e AgentConsole/engine-bridge`。
  - 資料庫：`pgvector/pgvector:pg18`（與 AutoClaude 共用同一映像）。DDL 以 PRD §6.2 為準，由後端 Flyway `V1__init.sql` 擁有。
  - 認證：JWT 最小實作——使用者清單放 `application.yml`（admin／operator／viewer 三角色各一組，密碼 bcrypt），無使用者管理 UI（PRD 沒要）。
- **資料庫 schema**：Console 九張表全部住 PostgreSQL 的 `console` schema（AutoClaude 的 alembic 已在 `public` 建同名 `checkpoints` 等表，共用同一 DB 會撞名）。後端 Flyway `spring.flyway.schemas=console`／`default-schema=console`、JPA `hibernate.default_schema=console`；Bridge 的 SQL 一律 `console.<table>`（環境變數 `BRIDGE_DB_SCHEMA`，預設 console）。
- **execution_runs 寫入分工（避免雙寫漂移，PRD §0.2.2）**：console-api（後端）只在建立時寫 `id, project_id, run_number, autonomy_level, scope, token_budget, dag, started_at`；Engine Bridge 擁有 `status, subprocess_pid, bridge_instance, advisory_lock_key, total_tokens_used, completed_at` 以及 `execution_steps`、`checkpoints` 兩表的所有寫入。後端對這些欄位只讀。
- **pause 語意（不改 AutoClaude）**：Bridge 設旗標，偵測到下一個步驟邊界（AutoClaude 每步結束會原子寫 `checkpoints/<playbook>.checkpoint.json`，以該檔 mtime／內容變化判斷）就送 SIGTERM 讓引擎乾淨退出 ⇒ 狀態 PAUSED；resume＝不帶 `--fresh` 重新 spawn（引擎自己從 checkpoint 續跑）；restore＝把指定歷史 checkpoint 複製成現用 checkpoint 再 spawn；stop＝SIGTERM，逾 30s 升 SIGKILL。
- **E2E 不靠真 Claude**：AutoClaude 支援 mock CLI——config.yaml `claude.command` 指到 `python -u <abs>/AutoClaude/tests/fixtures/dummy_cli.py`，playbook 各步用 `command:` 欄位（範例 `AutoClaude/tests/fixtures/mock_playbook.yaml`）。Brain（MiniMax）用 `AutoClaude/tools/mock_brain_server.py --port 9100`（OpenAI 相容格式）。所有自動化測試都用這兩個 mock；真 Claude 只留給掌舵者手動驗。

## 本 repo 的鐵律（違反＝push 被擋或 CI 紅）
1. 文件、註解、commit 訊息一律**繁體中文**（專有名詞保留原文）。
2. 所有文字檔 **LF 行尾**（`.gitattributes` 已設；`.sh` 若含 CR 會被 hook 擋）。
3. **不准 commit／push**。你只改工作樹；主控會驗證後 commit。
4. **不准寫任何真實機密**。`.env.example` 只放 `<YOUR_...>` 佔位符；pre-commit 有機密掃描。
5. 新的 `.sh` 必須 **shellcheck 乾淨**（根層 CI 與 pre-push 掃全 repo 的 `*.sh`）且 `bash -n` 過。
6. 新的 Python：`open()`／`read_text()`／`write_text()` **一律帶 `encoding="utf-8"`**；`os.replace`／`os.rename`／`shutil.move`／`Path.rename`／`Path.replace` 若非用不可，**呼叫點必須包在 `try: … except OSError:`（或 `PermissionError`）裡**——根層 `tools/tests/test_platform_neutral_paths.py::TestDirEntryPrimitivesAreAccountedFor` 掃全 repo `.py`，沒包就紅；不要用 `os.kill`／`signal` 以外的平台專屬 API 卻不罩 `sys.platform` 判斷；時間戳一律帶 tz（`datetime.now(timezone.utc)`），不准持久化 naive 本地時間。`ruff check <你的目錄>` 必須 0 錯（根 ruff.toml 用出廠預設規則）。
7. 不准動 `AutoClaude/`、`AISDLC_SDD/`、根層 `CLAUDE.md`、`.claude/`、`tools/`、`.github/`。
8. 暫存檔一律放 `/private/tmp/claude-501/-Users-wuweihong-Antigravity-AISDCL-Agent/6445bb47-f3aa-487f-98d0-691e7fd29e14/scratchpad/<你的角色>/`。
9. **不要**自己架背景等待（Monitor／sleep 迴圈）後就交卷——所有驗證在你交卷前同步跑完。**不要**再派子 agent。
10. 子代理交卷一律純文字——harness 拒寫報告類檔名是設計，不得以 heredoc 或換檔名繞過（Windows 上 Bash 工具另被鐵律一禁用）；報告落檔由主控做（OBS-SI-004／OBS-SI-200；原句「改用 Bash heredoc 落檔」於 2026-10-21 訂正）。
11. 工作中任何「我認為根因是 X」只是**待驗假設**，要用指令實證後才能寫成結論。

## 交卷格式（純文字，不要 JSON）
第一行固定：`STATUS: DONE` 或 `STATUS: PARTIAL` 或 `STATUS: BLOCKED`。
接著：
- 〈做了什麼〉逐條列檔案路徑。
- 〈驗證證據〉每道閘門一條：**完整指令** ＋ **逐字貼的關鍵輸出行**（例如 `BUILD SUCCESSFUL`、`N passed`、`rc=0`）。沒跑的就寫「未跑」，不准寫「應該會過」。
- 〈沒做／偏離〉逐條，附原因。
- 〈給主控的提醒〉下一位 agent 要知道的陷阱。
長證據落檔到你的 scratchpad 子目錄，交卷只貼路徑＋關鍵行。

## 🔴 跨平台（掌舵者 2026-10-14 補充：本輪做完會切到 Windows 繼續做）
下一輪在 **Windows 11 + PowerShell** 接續（那邊禁用 Bash 工具；pwsh 7 執行、腳本標的 PS 5.1 語意）。因此：
1. **文件裡的每一段指令都要雙形態**：bash 區塊 ＋ PowerShell 區塊並列。PowerShell 形態規則：**不准裸 `cd`／`Set-Location`**（要 `Push-Location <絕對或相對 AgentConsole 的路徑>; …; Pop-Location` 同一行成對）；venv 啟動寫 `.\.venv\Scripts\Activate.ps1`；Gradle 寫 `.\gradlew.bat`；不准 `VAR=value cmd` 前綴（改 `$env:VAR="value"; cmd`）；讀 rc 不接管線。
2. **Python（Bridge）必須在 Windows 也能跑**：結束子程序用 `proc.terminate()`／`proc.kill()`（portable），不要直接 `os.kill(pid, signal.SIGTERM)`；要用 `signal.SIGTERM` 等名稱時包 `if sys.platform != "win32"`；spawn 子程序時 Windows 用 `creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)`；「pid 是否存活」不准用 `os.kill(pid, 0)`（Windows 不支援），用 `psutil.pid_exists` 或 `ctypes OpenProcess`——擇一並寫清楚；路徑比對用 `Path(...).resolve()` 後再 `os.path.normcase()`（Windows 不分大小寫、有磁碟機代號）；檔案鎖：Windows 上開著的檔不能被改名／刪除，寫檔用「寫新檔→（try/except OSError）replace」；不要用 `fcntl`、`os.fork`、`pty`、unix socket。測試在 macOS 跑綠，但程式碼內凡平台相依處要留註解「Windows 行為＝…」。
3. **Shell 腳本只給容器內（Linux）用**，不要寫任何需要在 Windows 主機執行的 `.sh`；主機側操作用 `docker compose …` 指令（跨平台）或提供 `.ps1` 對等版（`.ps1` 必須 CRLF；含非 ASCII 時要 UTF-8 BOM）。
4. **Git 層**：`gradlew`（LF、索引模式 100755）與 `gradlew.bat`（CRLF）都要入庫；`.sh` 一律 LF；不要依賴 exec bit 以外的檔案屬性。
5. **路徑字面**：文件與程式碼內不准寫死 macOS 的 `/Users/...` 當常數（任務書裡的絕對路徑只是這台機器的現況）；設定一律走環境變數或相對 `AgentConsole/` 的路徑。
6. 交卷時加一節〈Windows 接續注意〉：列出你這塊在 Windows 上**還沒驗證**的點與驗證指令（PowerShell 形態）。

## 補充（Architect 交卷後，2026-10-14 晚）
- **checkpoint 真相**：AutoClaude **不寫步驟級 checkpoint**（Bridge 開發者對真引擎實證）。pause 的步驟邊界由 Bridge 解析引擎日誌「下一步驟啟動行」判定、Bridge 自己用引擎的 `FileStateRepository` 寫 checkpoint。細節以 `AgentConsole/docs/02_architecture/ADR-001-TechStack-Lock.md` D8 與 Bridge 交卷為準；**不要再假設「每步原子寫 checkpoint」**。Bridge 強制 `storage.mode ∈ {yaml_only, both}`，所以後端種子 `autoclaude.dalBackend` 預設 `FILE`。
- **文件寫法鎖**：教人跑腳本一律寫 `bash x.sh`／`sh gradlew`，不寫 `./x.sh`／`./gradlew`（根層 exec-bit 鎖只准 ONBOARDING §6 列名的檔為 100755；gradlew 入庫為 644，Dockerfile 內自己 `chmod +x`）。入庫的 `.md`／`.py` 內不得出現「pytest 摘要的英文通過／略過字樣＋四位數以上或帶千分位的數字」同一行（根層 pytest 基線站點鎖；用中文寫計數即可）。
- **外部網路可能被 auto-mode 分類器擋**（Architect 的 `curl -d` 被判 Exfil Scouting）。主控已預先：下載 Spring Boot 4.1.1 骨架到 `AgentConsole/backend/`（**不要重新生成**）、預熱 Gradle 相依快取。你若遇到網路呼叫被拒，**不要重試三次以上**，在交卷〈沒做〉寫明被擋的指令，繼續做不需網路的部分。
- **Architect 從 PRD 文字推得的缺陷（G-01～G-19，見 ADR-001 §5）**，與你相關者：nginx 只在 frontend-net 解析不到 backend（G-01，要加掛 backend-net）；`db-net internal: true` 下直接發布 5432／5433／5050 埠到主機不會通（G-02，正式 compose 不發布 DB 埠、開發用 `docker-compose.dev.yml` 覆蓋）；pgbackrest `apk`（G-03）；PRD 沒給 review／alerts 表（後端 V3／V4 增補，見 Architecture §11）。

## 補充二（Bridge 交卷後，2026-10-14 深夜；優先於上文衝突處）
- **E2E 的 Claude 替身＝`aisdlc-mock-claude`**（Bridge 自帶的 console script，裝在 `AgentConsole/engine-bridge/.venv/bin/`，Windows 在 `.venv\Scripts\aisdlc-mock-claude.exe`，Docker 映像內在 PATH）。原本「`claude.command` 指到 `python -u dummy_cli.py`」**行不通**（引擎不切分字串、`PlaybookTask.command` 零消費）。用法：`POST /autoclaude/runs` 的 `config_overrides.claude.command` 填 `aisdlc-mock-claude`；旋鈕走請求 `env`：`MOCK_CLAUDE_DELAY`／`MOCK_CLAUDE_TRACE`／`MOCK_CLAUDE_FAIL_REGEX`／`MOCK_CLAUDE_IGNORE_TERM`（細節見 `AgentConsole/engine-bridge/README.md`）。
- **Bridge 實際契約以 `AgentConsole/engine-bridge/README.md` 與其 `tests/` 為準**（Architecture §10 的差異清單待主控回寫）。後端要知道的重點：pause 只收 RUNNING、resume 只收 PAUSED、stop 收 RUNNING／PAUSING／PAUSED、restore 收 PAUSED 或終態，其餘 409 `invalid_state`；重複 run_id 409 `run_exists`；`GET …/events` 回裸陣列；SSE `data` 是扁平封包；resume 後同一步會再發一次 STARTED；ESCALATION／Token halt 判 FAILED 並發 `alert`；`review-request` 事件目前從不發送（審核流程由後端依自治等級自己產生）；`config_overrides` 不收 `storage`／`checkpoint_dir`（Bridge 固定 yaml_only、落點在 `<workspace>/<run_id>/engine/`）；機密只能走 `env`；只有帶 UUID `goal_task_id` 的步驟才寫 `console.execution_steps`。
- **compose 對 Bridge 的要求**：整個 `AISDLC_SDD/` 唯讀掛成 `/sdd` 並設 `SDD_ROOT=/sdd`；`ENGINE_WORKSPACE=/workspace` 掛 named volume（映像以 uid 10001 非 root 執行，volume 須對它可寫——用 `user:` 或 entrypoint chown）；要讓引擎改主機專案目錄就 bind mount 並把掛載點加進 `BRIDGE_ALLOWED_PATH_ROOTS`；`BRIDGE_DB_DSN`＋`BRIDGE_DB_SCHEMA=console`；`BRIDGE_OUTBOUND_ALLOWLIST=api.minimax.io,api.minimax.chat`（全棧不含 loopback）；uvicorn 單一 worker。
- **Docker 映像 build context**：Bridge 的 Dockerfile 有 `Dockerfile.dockerignore`（BuildKit），context 約 4MB；基底 `python:3.11-slim` 可用 `--build-arg PYTHON_IMAGE=python:3.11` 改用本機快取。
