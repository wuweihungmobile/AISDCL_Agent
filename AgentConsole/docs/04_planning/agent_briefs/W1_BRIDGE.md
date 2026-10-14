# 任務書 W1-B：Engine Bridge 開發者（FastAPI 旁車，PRD §0.2／§11.8）

> 先讀 `COMMON_CONTEXT.md`（同目錄），再讀本檔。Architect 正在並行寫文件，**你不要等他**；契約以本檔〈API 契約〉為準（兩邊同一份）。

## 你的角色
你是 Engine Bridge 的唯一開發者。Bridge 是一個 Python 3.11 + FastAPI 薄旁車，把兩個純 CLI 引擎（AutoClaude、AISDLC_SDD）包成 REST + SSE，給 Spring Boot 後端呼叫。**零侵入**：不改 `AutoClaude/`、`AISDLC_SDD/` 任何檔。

## 必讀
1. PRD `docs/01_requirements/Agent_ConsoleUI_PRD.md` 的 §0.1～§0.6（行 40～125）、§5.3（行 821～1030）、§7.1.5／§7.1.7（行 1748～1790）、§11.8（行 2799～2862）。
2. `AutoClaude/autoclaude/main.py`（CLI 參數、config 載入）、`AutoClaude/config.yaml`（可覆寫鍵：claude.command／extra_args、minimax.*、token_guard.*、storage.mode、playbook.*）、`AutoClaude/autoclaude/utils/config.py`（AppConfig 結構）。
3. `AutoClaude/autoclaude/models/playbook.py`（Playbook／PlaybookTask 欄位；`goal_task_id` 用來帶 console 的 task UUID）。
4. `AutoClaude/autoclaude/utils/checkpoint_manager.py` ＋ `AutoClaude/autoclaude/plugins/checkpoint_plugin.py`：**實證** checkpoint 檔名（`<playbook stem>.checkpoint.json`）、寫入時機（每步結束？）、目錄（相對 cwd 的 `checkpoints/`，可否由 config 指定）。你的 pause 設計靠它。
5. `AutoClaude/tests/fixtures/mock_playbook.yaml` ＋ `dummy_cli.py`：mock CLI 的用法（config `claude.command` 指到 `python -u <abs>/dummy_cli.py`，playbook 步驟用 `command:`）。
6. `AutoClaude/autoclaude/execution/goal_decomposer.py`（decompose／approve／DecompositionError）、`AutoClaude/autoclaude/core/wiring.py::build_goal_decomposer`、`AutoClaude/autoclaude/infra/adapters/minimax_brain.py`（IBrain 實作）、`AutoClaude/tools/mock_brain_server.py`（OpenAI 相容 mock，`--port 9100`；decompose 的回應格式請看它有沒有支援 `DecompositionDecision`，沒有的話你在測試裡用自己的 FakeBrain 實作 IBrain）。
7. `AutoClaude/autoclaude/infra/adapters/sdd_to_playbook_adapter.py`：`load_spec`／`compile_tasks`／`_assert_frozen`／黑名單字元集常數；`AutoClaude/tests/` 內它的測試（找 spec 目錄 fixture 的做法）。
8. `AISDLC_SDD/AISDLC_SDD_v0.30/build/reports/fsm/`（FSM-STATE-*.yaml 長相）。

## 要建的東西（全部在 `AgentConsole/engine-bridge/`）
```
pyproject.toml          fastapi, uvicorn[standard], pydantic>=2, pyyaml, psycopg[binary,pool]>=3, httpx(測試), pytest, pytest-asyncio, ruff；[project.scripts] 可選
Dockerfile              python:3.11-slim；build context＝monorepo 根（COPY AutoClaude/ 與 AgentConsole/engine-bridge/）；pip install 兩者；CMD uvicorn app.main:app --host 0.0.0.0 --port 8081
app/main.py             FastAPI app、lifespan（啟動做孤兒回收）、/health、掛兩個 router
app/settings.py         pydantic-settings 或 os.environ：BRIDGE_PORT=8081、ENGINE_WORKSPACE（預設 <engine-bridge>/.workspace，gitignore）、AUTOCLAUDE_ROOT（預設 ../../AutoClaude 絕對化）、SDD_ROOT（預設＝`../../AISDLC_SDD/AISDLC_SDD_v*` 數字最大者）、BRIDGE_DB_DSN（可選；無則純檔案模式）、BRIDGE_INSTANCE（預設 hostname+pid+uuid4）、BRIDGE_STOP_GRACE_SECONDS=30、BRIDGE_ALLOWED_PATH_ROOTS（冒號分隔；預設 ENGINE_WORKSPACE 與 monorepo 根）、BRIDGE_OUTBOUND_ALLOWLIST（預設 api.minimax.io,api.minimax.chat,localhost,127.0.0.1）
app/models.py           Pydantic 請求／回應模型（照〈API 契約〉）
app/security.py         NFR-SEC-03：execution_path 必須絕對、存在、位於 allowlist root 之下（realpath 後比對，擋 `..` 與 symlink 逃逸）；playbook 每個 evaluator_command 套與 SddToPlaybookAdapter 同一組黑名單字元集（`{ ! ` > < ~ $ & ; }`，請從 adapter 原始碼讀出常數並寫 parity 測試），違者 422 列出違規字元與步驟。NFR-SEC-04：外呼（MiniMax base_url）host 必在 allowlist，否則拒絕並審計 log。
app/events.py           EventStore：每個 run 一個 `events.jsonl`（append-only，`encoding="utf-8"`）＋記憶體環；seq 單調遞增；`replay(after, limit)`；SSE 串流從 after 開始先重播再 tail。
app/runner.py           RunManager：spawn `[sys.executable,"-m","autoclaude",playbook_path,"--config",config_path,(--fresh)]`，cwd＝execution_path，env＝os.environ 合併請求 env；用執行緒讀 stdout/stderr 逐行 → log 事件；解析引擎輸出判 step 事件（找 AutoClaude 印的步驟開始／完成字樣，實證後寫 regex，並留一個「無法解析就只發 log」的退路）；checkpoint 監看（0.5s 輪詢 mtime，變化→發 step 事件並讀 step_idx）；pause/resume/stop/restore 語意照 COMMON_CONTEXT；process 退出→COMPLETED（rc=0）/FAILED（其他）/CANCELLED（stop 導致）；run 狀態持久化到 `<workspace>/<run_id>/run.json`（含 pid、bridge_instance、status）；啟動時掃 workspace 把 RUNNING 但 pid 不存活的 run 標 FAILED reason=orphaned 並釋放鎖。
app/locks.py            AdvisoryLock：DB 模式用專用連線 `SELECT pg_try_advisory_lock(hashtext(%s))`（key＝`project||':'||execution_path`），run 終態時 unlock；檔案模式用行程內 dict 鎖同鍵；取不到→409。
app/db.py               DB 模式才啟用：psycopg pool；只寫 `execution_runs.{status,subprocess_pid,bridge_instance,advisory_lock_key,total_tokens_used,completed_at}`（UPDATE … WHERE id=run_id；列不存在就跳過並 log）；INSERT `execution_steps`（task_id 取 playbook task 的 goal_task_id；沒有就不寫 DB 只留事件）、`checkpoints`（state_snapshot＝checkpoint json）。表結構照 PRD §6.2。
app/routers/autoclaude.py  〈API 契約〉/autoclaude/* 全部
app/routers/sdd.py         /sdd/version、/sdd/fsm/{project}、/sdd/compile
tests/                  見下
README.md               怎麼裝、怎麼跑、環境變數表
.gitignore              .venv/ .workspace/ __pycache__/
```

## API 契約（與 Architect 同一份；逐字實作）
（見 `W1_ARCHITECT.md`〈Engine Bridge API 契約〉一節——同目錄，請直接讀那一段，不另抄一份以免兩份漂移。）

## 測試要求（pytest，不需 DB、不需真 Claude；DB 整合測試只在 `BRIDGE_TEST_DSN` 有設時跑）
1. 生命週期 E2E：用 mock_playbook（三步）＋ dummy_cli：POST runs → 串流讀到 ≥3 個 step COMPLETED → 終態 COMPLETED；run.json 與 events.jsonl 存在。
2. pause 在步驟邊界：啟動後立刻 pause → 狀態先 PAUSING → 第一步 checkpoint 寫出後轉 PAUSED 且 process 已退出；resume → 跑完剩下步驟（實證 completed_steps 從 checkpoint 接續，不是從頭）。
3. stop：RUNNING 中 stop → CANCELLING → 子程序消失 → CANCELLED。
4. restore：完成後列 checkpoints 非空；restore 指定一筆 → 新 spawn 從該點續跑。
5. 409：同 project+execution_path 第二個 POST runs 回 409 並帶 holder_run_id；第一個終態後可再 POST。
6. 422 消毒：evaluator_command 含 `;`／`$(`／`` ` `` 任一 → 422 列出違規；execution_path 用 `..` 逃逸或不在 allowlist root → 422。
7. SSE 重播：先讀到 seq=N 斷開，`?after=N` 重連只收 >N；`/events?after=` 回同一批。
8. 孤兒回收：手工寫一個 run.json（status RUNNING、pid＝不存在的 pid）→ 啟動 app → 狀態變 FAILED reason=orphaned。
9. decompose：FakeBrain（實作 IBrain，`supports_decomposition=True`）回 3 步 DAG → 200 且 signed_off=false；回 25 步 → 422 gate=max_steps；回有環 → 422 gate=cycle；回空 prompt → 422 gate=empty_prompt；approve 空 approver → 400；approve 後 signed_off=true 帶 approver/approved_at。
10. sdd：`/sdd/version` 回 v0.30；`/sdd/fsm/不存在` 404；用 tmp SDD_ROOT 放一支 FSM-STATE-demo.yaml → 200 含 current_state。
11. security parity：你的黑名單字元集 == adapter 原始碼裡的常數（測試直接 import 讀）。
12. 外呼 allowlist：config_overrides 把 minimax.base_url 指到 `http://evil.example` → 422；指到 `http://localhost:9100/...` → 放行。

## 閘門（交卷前自己跑，逐字貼關鍵行）
```
cd /Users/wuweihong/Antigravity/AISDCL_Agent/AgentConsole/engine-bridge
uv venv .venv && . .venv/bin/activate && uv pip install -e . -e ../../AutoClaude
ruff check .                      # 期望：All checks passed!
python -m pytest -q               # 期望：N passed，0 failed；貼 N
uvicorn app.main:app --port 8081 & sleep 2; curl -s localhost:8081/health; kill %1    # 貼 JSON
cd /Users/wuweihong/Antigravity/AISDCL_Agent/tools/tests && python -m unittest test_platform_neutral_paths.TestDirEntryPrimitivesAreAccountedFor -v   # 期望 OK（這支掃全 repo .py）
cd /Users/wuweihong/Antigravity/AISDCL_Agent && ruff check AgentConsole/engine-bridge   # 根 ruff.toml 視角也要過
docker build -f AgentConsole/engine-bridge/Dockerfile -t aisdlc-engine-bridge:dev .   # 期望 build 成功；再 docker run --rm -p 8081:8081 … curl /health
```
Docker 若因網路慢而超過 10 分鐘，寫「未完成」並附最後 20 行，不要硬等。

## 給你的提醒
- AutoClaude 的 `python -m autoclaude` 在 cwd 下建 `checkpoints/`、`logs/`；你的 execution_path 測試用 tmp 目錄。
- dummy_cli 有隨機授權提示（`AUTH_RANDOM_PROB=0.6`）——AutoClaude 的 `loop.auth_patterns` 會自動回 y；若測試 flaky，看 dummy_cli 有沒有環境變數可把機率關掉，沒有就把 playbook 只用 `step1`/`ping`（不需授權的指令）。
- 時間戳一律 `datetime.now(timezone.utc).isoformat()`。
- 不准用 `os.replace` 做原子寫入，除非包在 `try/except OSError`。
- 你交卷時請把〈API 契約〉實際落地的差異（如果有）逐條列出，主控要回寫文件。
