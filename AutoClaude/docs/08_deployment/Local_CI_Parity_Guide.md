# Local CI Parity Guide — 本機 CI 對等與「上版前本機全綠」SOP

**版本**：v1.0 | **建立**：2026-06-11 | **適用**：AutoClaude SD_09+

> **目的**：根本解決「push 到 GitHub 才發現 CI/CD 紅燈」。把 CI 的把關**前移到本機**，
> 善用本機已安裝的 Docker，在 Linux 容器內重現雲端流程，**本機全綠才 push**。

---

## 0. 根因：為什麼 push 後才爆？

| 差異來源 | 本機（開發） | CI（GitHub Actions） | 過去的紅燈例（sprint_history） |
|---------|------------|---------------------|------------------------------|
| OS | Windows 11 | ubuntu-latest（Linux） | `.sh` CRLF → bash `$'\r'`（紀律 #8） |
| PG 鏡像 | docker-compose `pg18` | service `pgvector:pg17` | extension/alembic 行為差（R56 P0-1d/1e） |
| 依賴 | 平台相依（wexpect win32） | `pip install -e .[dev,postgres]` | 缺 psycopg2 → alembic 掛（R56 P0-1c） |
| 觸發 job | 只手動跑 pytest | test/equivalence/claude-md/pg-contract | push gate job 從未本地跑過 |

**結論**：唯有「在 Linux 容器內、用 CI 同款鏡像、跑 CI 同一份 workflow」才能在本機重現並修復。

---

## 1. 四大支柱（對應需求一～四）

### 一、迷你正式環境（Docker Compose）
- [`docker-compose.yml`](../../docker-compose.yml)：完整 dev/prod 棧（PG **pg18** + TEI embedder）。
- [`docker-compose.ci.yml`](../../docker-compose.ci.yml)：**CI 對等** PG（**pg17**，精準對齊 `ci.yml` service）。
  本地驗證 PG 相依測試時用此檔，避免 pg18/pg17 漂移造成「本機過、CI 爆」。
  > ⚠️ CI 改 PG 版本時**必須同步本檔**，否則本地驗證失真。

```powershell
docker compose -f docker-compose.ci.yml up -d      # 起 pg17（與 CI 同款）
# ... 跑 alembic / pytest ...
docker compose -f docker-compose.ci.yml down -v     # 用完即丟（tmpfs，無殘留）
```

### 二、地端直接跑 GitHub Actions（act）
- 工具：`act`（nektos/act）— 安裝：`winget install --id nektos.act`（或 `scoop install act`）。
  `run_act.ps1` 會自動定位 act（含 winget 安裝路徑），未裝時印安裝指引。
- 設定：[`.actrc`](../../.actrc)（runner = `catthehacker/ubuntu:act-latest`，`linux/amd64`）。
- 載具：[`tools/run_act.ps1`](../../tools/run_act.ps1) — 自動定位 act、檢查 Docker、跑 `ci.yml`。

```powershell
powershell -ExecutionPolicy Bypass -File tools/run_act.ps1 -List          # 看 ci.yml 有哪些 job
powershell -ExecutionPolicy Bypass -File tools/run_act.ps1 -Job test       # 最快：只跑主測試閘門（Linux 容器內）
powershell -ExecutionPolicy Bypass -File tools/run_act.ps1                  # 完整：push 全部 gating job
```
- nightly/排程 job（mutation/pg-e2e/perf）以 `if: schedule` 排除，push 事件不觸發 →
  本地 nightly 改用 [`tools/run_local_nightly.ps1`](../../tools/run_local_nightly.ps1)。
- 鏡像策略：`run_act.ps1` 先以 `docker pull` 備妥 runner（+ 完整 push 時的 `pgvector:pg17`），
  再對 act 傳 `--pull=false` 用本地鏡像 —— 繞過「Docker Desktop credsStore 對公開鏡像誤送認證 →
  Docker Hub 回 401」的 act forcePull bug（本機實測根因）。首次約 pull 1~1.5GB，之後重用。

### 三、自動攔截點（Pre-commit Hooks）
- 原生 git hooks（零依賴、推薦）：[`tools/git-hooks/`](../../tools/git-hooks/)
  - `pre-commit`：ruff / LOC 預算 / CLAUDE.md≤400 / `.sh` LF（快，< 15s）
  - `pre-push`：pytest + import-linter + snapshot（**完整本機 CI 閘門**）
- 安裝：

```powershell
powershell -ExecutionPolicy Bypass -File tools/install_git_hooks.ps1            # 設 core.hooksPath=tools/git-hooks
powershell -ExecutionPolicy Bypass -File tools/install_git_hooks.ps1 -Uninstall # 還原
```
- 框架版（選用）：[`.pre-commit-config.yaml`](../../.pre-commit-config.yaml)（`pip install pre-commit && pre-commit install`），委派同一組原生 hook（SSOT，紀律 #4）。
- 緊急跳過：`AUTOCLAUDE_SKIP_HOOKS=1` 或 `git commit/push --no-verify`。

### 四、高擬真 API 與 AI 模型模擬
- **執行端（Claude Code CLI）Mock**：既有 [`tests/fixtures/dummy_cli.py`](../../tests/fixtures/dummy_cli.py)。
- **決策端（Brain/Minimax LLM）Mock**：[`tools/mock_brain_server.py`](../../tools/mock_brain_server.py)
  — OpenAI-compatible，回應契約對齊 `minimax_client._parse_response`，過 Hallucination Guard。
- **本地真模型（vLLM/Qwen GGUF）**：[`docker-compose.llm.yml`](../../docker-compose.llm.yml)。

```powershell
# 確定性 Mock（CI/離線首選）
docker compose -f docker-compose.llm.yml --profile mock up -d
$env:MINIMAX_BASE_URL = "http://localhost:9100/v1/chat/completions"; $env:MINIMAX_API_KEY = "mock"

# 真模型 vLLM（需 GPU）
docker compose -f docker-compose.llm.yml --profile llm up -d
$env:MINIMAX_BASE_URL = "http://localhost:8000/v1/chat/completions"
$env:MINIMAX_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
```
- 接線原理：`main.py` 以 `MINIMAX_BASE_URL` / `MINIMAX_MODEL` env 覆蓋 `config.yaml`。
- GGUF 量化：vLLM 對 GGUF 支援實驗性；**真 GGUF** 建議改 `llama.cpp` server
  （`ghcr.io/ggml-org/llama.cpp:server`，`--hf-repo <Qwen GGUF> -c 8192`，同樣 `/v1/chat/completions`）。

---

## 2. 標準工作流（push 前 SOP）

```powershell
# 一鍵本機 CI 閘門（鏡像 ci.yml push jobs）—— 全綠才 push
powershell -ExecutionPolicy Bypass -File tools/local_ci_gate.ps1            # LOC/CLAUDE.md/snapshot/import-linter/pytest
powershell -ExecutionPolicy Bypass -File tools/local_ci_gate.ps1 -Act        # 再加 Linux 容器真 CI（最嚴格）
powershell -ExecutionPolicy Bypass -File tools/local_ci_gate.ps1 -Pg         # 再加 pg17 PG 契約測
```

安裝 hooks 後，`git commit` / `git push` 會**自動**跑對應檢查，無需記憶。

決策樹：
- 日常 commit → hook `pre-commit` 自動把關。
- push 前 → `local_ci_gate.ps1`（純 Python 檢查，快）；遇 Windows/Linux 疑慮 → 加 `-Act`。
- 動到 PG/alembic/schema → `local_ci_gate.ps1 -Pg` 或 `run_act.ps1`（完整）。
- 動到 nightly（mutation/perf/pg-e2e）→ `run_local_nightly.ps1`。

---

## 3. 故障排除

| 症狀 | 處置 |
|------|------|
| `act: command not found` | 重開 shell（PATH 已改）或 `run_act.ps1` 自動定位 winget 路徑；或 `scoop install act` |
| act 首次很慢 | 首次 `docker pull` runner 鏡像（1~1.5GB）；之後重用本地鏡像 |
| act `authentication required - incorrect username or password` | Docker Desktop credsStore 對公開鏡像誤送認證；`run_act.ps1` 已用 `docker pull`+`--pull=false` 繞過。直接跑 act 時請先 `docker pull catthehacker/ubuntu:act-latest` |
| act 報 Docker 連線失敗 | 開啟 Docker Desktop；`docker info` 應成功 |
| pre-push pytest 太久 | `AUTOCLAUDE_PUSH_PYTEST_ARGS="tests/xxx -q"` 縮限；或先 `local_ci_gate.ps1` |
| hook 沒觸發 | 確認 `git config --get core.hooksPath` = `tools/git-hooks`；重跑安裝腳本 |
| `.sh` 在容器噴 `$'\r'` | `.gitattributes` 已強制 LF；重新 checkout 或 `dos2unix` |
| PG 測試本機過 CI 爆 | 確認用 `docker-compose.ci.yml`（pg17）而非主 compose（pg18） |

---

## 4. 檔案清單（本次新增/異動）

| 檔案 | 角色 |
|------|------|
| `docker-compose.ci.yml` | CI 對等 PG（pg17） |
| `docker-compose.llm.yml` | mock-brain / vLLM 本地 LLM |
| `.actrc` | act runner 設定 |
| `tools/run_act.ps1` | act 本地 CI 載具 |
| `tools/git-hooks/{pre-commit,pre-push}` | 自動攔截點 |
| `tools/install_git_hooks.ps1` | hooks 安裝/移除 |
| `.pre-commit-config.yaml` | pre-commit 框架（選用） |
| `tools/mock_brain_server.py` | 高擬真 Brain Mock |
| `tools/local_ci_gate.ps1` | 一鍵本機 CI 閘門 |
| `tests/tools/test_mock_brain_server.py` | mock 契約測試（紀律 #4） |
| `autoclaude/main.py` | 加 `MINIMAX_BASE_URL/MODEL` env 覆蓋 |
| `.env.example` / `.gitattributes` | 接線文件 + hook LF |
