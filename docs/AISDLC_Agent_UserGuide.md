# AISDLC_Agent 安裝部署使用手冊（User Guide）

> **本手冊範圍**：涵蓋 `AISDLC_Agent` monorepo 的安裝、啟動、使用、關閉四大環節。
> 本 repo 由**兩個子專案**組成：
> - **AutoClaude**（`AutoClaude/`）— 真正的**執行引擎**（Python 3.11+ 應用），驅動 Claude Code CLI 依序執行多步驟 Playbook。**可被啟動／關閉的就是它。**
> - **AISDLC_SDD**（`AISDLC_SDD/`）— **方法論框架**（~85% Markdown 模板/Agent/Workflow + ~15% Python FSM runtime），是 AutoClaude 可驅動的對象（`workflow_type: aisdlc / aisdlc_sdd`）。
>
> 因此本手冊以 **AutoClaude 引擎為操作主體**，AISDLC_SDD 框架作為其驅動對象一併說明。
>
> **最後更新**：2026-06-15 ｜ **適用版本**：AutoClaude 0.1.0（Level 5）/ AISDLC-SDD v0.01

---

## 目錄

1. [系統需求與前置條件](#0-系統需求與前置條件)
2. [如何安裝部署 AISDLC_Agent](#1-如何安裝部署-aisdlc_agent)
3. [如何啟動 AISDLC_Agent](#2-如何啟動-aisdlc_agent)
4. [如何使用 AISDLC_Agent](#3-如何使用-aisdlc_agent)
5. [如何關閉 AISDLC_Agent](#4-如何關閉-aisdlc_agent)
6. [疑難排解（FAQ）](#5-疑難排解-faq)

---

## 0. 系統需求與前置條件

| 項目 | 需求 | 說明 |
|------|------|------|
| 作業系統 | macOS ⇄ Windows 11（雙平台對等）/ Linux | 雙平台開發完全相容（工具鏈對照見根層 [ONBOARDING.md](../ONBOARDING.md)）；CI 對等於 ubuntu-latest |
| Python | **3.11+**（強制） | `pyproject.toml` 宣告 `requires-python = ">=3.11"` |
| Claude Code CLI | 已安裝且可執行 `claude` | AutoClaude 透過 PTY/subprocess 包裝 Claude Code，**這是必要前置** |
| Git | 已安裝 | CrossStepValidator 以 `git status` 偵測步驟間污染 |
| Minimax API Key | 必填（修正大腦用） | 從 [platform.minimax.io](https://platform.minimax.io)（國際版）或 platform.minimaxi.com（中國版）取得 |
| Docker Desktop | 選配 | 本機 CI 對等 / Nightly / PostgreSQL 後端時才需要 |
| PostgreSQL 17 + pgvector | 選配 | 僅 `both` / `db_only` 儲存模式需要；預設 `yaml_only` 不需要 |
| Java + tla2tools.jar | 選配 | 僅跑 AISDLC_SDD 的 TLA+/TLC 形式化驗證時需要 |

> 🔴 **語言規範**：本 workspace 下所有對話回覆必須使用**繁體中文**（專有名詞如 AISDLC、SDD、API、Docker、pytest 保持原文）。

---

## 1. 如何安裝部署 AISDLC_Agent

### 1.1 取得程式碼

```bash
# 若尚未取得（已脫離巢狀 .git，現為單一 monorepo）
git clone <repo-url> AISDLC_Agent
cd AISDLC_Agent
```

工作目錄根即 clone 目的地（monorepo 根），底下含 `AutoClaude/`、`AISDLC_SDD/` 兩個子專案與根整合層 `docs/`。

### 1.2 安裝 AutoClaude 引擎（核心）

> 🔴 **環境建置一律依根層 [ONBOARDING.md](../ONBOARDING.md) §1~§4**，以 bootstrap 一鍵完成，
> **請勿在 `AutoClaude/` 下自建 venv**（會與根層 `.venv` SOP 相衝）。

```bash
# 在 monorepo 根目錄執行（macOS / Linux）
bash tools/bootstrap.sh
# Windows（PowerShell）：
# powershell -ExecutionPolicy Bypass -File tools/bootstrap.ps1
```

bootstrap 會：檢查 Python ≥3.11 → 建立**根層** `.venv` → 安裝 AutoClaude（editable，`[dev,notifications,lint]`，含 pytest / ruff / hypothesis / import-linter / 桌面通知）+ AISDLC_SDD CI 依賴。

每個新終端機、每次開發前啟用根層 venv（🔴 必要，詳見 ONBOARDING.md §3）：

```bash
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\Activate.ps1     # Windows（PowerShell）
```

#### 選配：PostgreSQL 後端（僅生產/灰度需要）

```bash
# 啟用根層 venv 後，在 AutoClaude/ 目錄下執行
# 🔴 若根層 .venv 是 bootstrap 用 uv 建的（偵測到 uv 時的預設路徑），venv 內部沒有
#    pip 模組（python -m pip 會報 No module named pip，實機驗證重現），一律改用
#    uv pip install（uv 已安裝時對任何已啟用 venv 皆可用）；只有走傳統
#    python -m venv 回退路徑（未裝 uv）才會有 pip 模組可直接用 pip install。
uv pip install -e '.[postgres]'            # SQLAlchemy + asyncpg + psycopg2 + alembic + tenacity + cachetools
uv pip install -e '.[postgres,pgvector]'   # 再加 pgvector 向量查詢
```

> ⚠️ `alembic` 走同步連線，需 `psycopg2-binary`（已含於 `[postgres]` extra）；缺少時 `alembic upgrade head` 會報 `ModuleNotFoundError`。

### 1.3 設定環境變數與設定檔

> ⚠️ **路徑陷阱**：以下指令在 **`AutoClaude/` 子目錄**下執行（不是 monorepo 根）。

```bash
# 1) API 憑證（.env 已被 .gitignore 排除，絕不會 commit）
cp .env.example .env
# 編輯 .env，至少填入 MINIMAX_API_KEY
#   ⚠️ API key 來源平台必須與 endpoint 區域對齊：
#      國際版 key → MINIMAX_BASE_URL=https://api.minimax.io/v1/text/chatcompletion_v2
#      中國版 key → MINIMAX_BASE_URL=https://api.minimaxi.com/v1/text/chatcompletion_v2
#   區域不匹配會回 base_resp.status_code=2049 "invalid api key"

# 2) 個人化設定檔（gitignored）
cp config.yaml.example config.local.yaml
# 編輯 config.local.yaml，依需要調整 loop / playbook / token_guard / storage 等區段
```

**儲存模式（`config.local.yaml` 的 `storage` 區段）** — 預設 `yaml_only` 即可，零部署成本：

```yaml
storage:
  mode: "yaml_only"   # yaml_only（預設）| both（灰度雙寫）| db_only（生產）
  # db_dsn: "postgresql+asyncpg://user:pass@host:5432/db?sslmode=require"
```

> DSN 解析優先序：環境變數 `AUTOCLAUDE_DB_DSN` > `AUTOCLAUDE_PG_DSN`（deprecated）> `config.storage.db_dsn`。
> 🔴 生產 DSN 必須含 `?sslmode=require`；僅本機 dev 可設 `AUTOCLAUDE_ALLOW_INSECURE_DB=1` 跳過 TLS。

### 1.4 驗證安裝（強制）

依專案「開發-編譯-測試循環」紀律，安裝後**立即驗證**：

**macOS / Linux（bash・zsh）**

```bash
# 在 AutoClaude/ 目錄下
python -m pytest tests/ -q          # 全套測試（🔴 基線 passed/skipped 數字唯一出處＝根層 ONBOARDING.md §7，本檔不重複數字）
PYTHONUTF8=1 lint-imports           # 架構約束：8 kept / 0 broken（需先裝 [lint]）
ruff check .                        # lint（line-length=100, py311）
```

**Windows（PowerShell）**

```powershell
# 在 AutoClaude\ 目錄下
python -m pytest tests/ -q          # 全套測試（基線數字同上，見 ONBOARDING.md §7）
$env:PYTHONUTF8=1; lint-imports     # 架構約束：8 kept / 0 broken（需先裝 [lint]）
ruff check .                        # lint（line-length=100, py311）
```

> 🔴 上面兩塊的差別不是排版偏好：`VAR=value <指令>` 這種前綴語法**在 PowerShell 不存在**，
> 照抄 bash 版會得到 `The term 'PYTHONUTF8=1' is not recognized`（設環境變數須寫
> `$env:VAR=值; <指令>`）。R57 已為 `ONBOARDING.md` §7 補過同一件事，本檔（以及使用者
> 最先讀到的「強制驗證」步驟）當時漏補，R59 補齊（DEF-101-513）。
>
> 🔴 本節**刻意不寫死** passed/skipped 數字：`ONBOARDING.md` §7 是全 repo 基線數字的唯一
> 站點，由 `tools/check_pytest_baseline_sites.py` 機械守門。本檔原先自帶一組寫死的舊數字，
> 而實測值早已成長到三千多 passed／兩百多 skipped——差距是數百支的量級；更關鍵的是
> **本檔當時不在守門的掃描面內**，所以這個數字腐化了很多輪都不可能翻紅。對照組：照著
> 「強制驗證」步驟做的新使用者，量到的數字與文件差幾百支，合理反應是判斷「安裝壞了」。
> R59 已把本檔一併納入該守門的掃描面（DEF-101-514）。

全綠代表 AutoClaude 引擎安裝成功。

### 1.5（選配）安裝 AISDLC_SDD 框架驗證環境

僅在需要驅動 SDD 方法論或修改框架時才需要：

```bash
cd ../AISDLC_SDD
bash scripts/ci-gate.sh             # 本機 CI 閘門：pytest（含 offline reachability BFS）+ arch_fitness --strict
# 進階：bash scripts/ci-gate.sh --full-tlc   # 另跑五軌 TLA+/TLC（需 Java + tla2tools.jar）
```

框架入口文件（使用前必讀）：[AISDLC_SDD/AISDLC_SDD_v0.01/AISDLC_SDD_INIT.md](../AISDLC_SDD/AISDLC_SDD_v0.01/AISDLC_SDD_INIT.md)。

### 1.6（選配）部署 PostgreSQL 後端

```bash
cd AutoClaude

# 1) 起 CI 對等 PG（pg17）
docker compose -f docker-compose.ci.yml up -d

# 2) 執行 migrations（0001 → 最新）
export AUTOCLAUDE_DB_DSN="postgresql+asyncpg://autoclaude:autoclaude@localhost:5432/autoclaude?sslmode=disable"
export AUTOCLAUDE_MIGRATE_DSN="$AUTOCLAUDE_DB_DSN"
alembic upgrade head

# 3) config.local.yaml 切 storage.mode: "both"（灰度）
```

> ⛔ **生產上線紅線**：切換 `db_only` 前須 `both` 模式 ≥ 24h 且 metrics 全零、PM + Stakeholder 簽核、由人類 DBA 在 staging（≥1M 真實列）重跑。詳見 `AutoClaude/docs/08_deployment/DB_Only_Switch_Runbook.md`。

---

## 2. 如何啟動 AISDLC_Agent

AutoClaude 的「啟動」＝以一份 Playbook（YAML）為輸入執行引擎。**啟動前須先有 Playbook**（見 [3.1](#31-撰寫-playbook)）。

### 2.1 基本啟動指令（在 `AutoClaude/` 目錄下）

```bash
# 方式 A：module 形式
python -m autoclaude <playbook.yaml> --config config.local.yaml

# 方式 B：安裝後的 entrypoint（pip install -e 後可用）
autoclaude <playbook.yaml> --config config.local.yaml
```

### 2.2 啟動參數

| 參數 | 說明 |
|------|------|
| `<playbook.yaml>` | **必填**，要執行的 Playbook 路徑（例如 `scripts/example_playbook.yaml`） |
| `--config <file>` | 設定檔路徑，建議用個人化的 `config.local.yaml` |
| `--fresh` | **忽略既有 checkpoint，從頭重跑**（不續傳） |

### 2.3 啟動範例

```bash
# 用內建範例 Playbook 試跑（AISDLC_SDD TDD 開發循環範本）
python -m autoclaude scripts/example_playbook.yaml --config config.local.yaml

# 從頭重跑（忽略 checkpoint）
python -m autoclaude scripts/my_playbook.yaml --fresh

# SDD 橋接冒煙測試
python -m autoclaude scripts/sdd_bridge_smoke.yaml --config config.local.yaml
```

### 2.4 啟動後的執行流程（狀態機閉環）

啟動後引擎進入狀態機，自動完成下列閉環，**無需人工逐步介入**：

```
INIT → PRE_RUN_VALIDATE → CONTEXT_NEGOTIATION → EXECUTE(step N)
                                                    ↓ （Token Guard 監控）
                                          ≥80% → /compact（注入 [GLOBAL_GOAL] anchor）
                                          ≥90% → 儲存 checkpoint 並排程恢復
                                                    ↓
                                                EVALUATE
                                          成功 ┘     └ 失敗 → Minimax CORRECTION
                                            ↓                 → retry / ESCALATION
                                      next step                  → 自演化（Minimax→規則）
                                            ↓
                                          DONE → GOAL_SYNTHESIS（全局目標驗證）→ 桌面通知
```

> 啟動成功的徵兆：終端開始依序送 prompt 給 Claude Code、自動回應授權提示（`Y/n`）、每步驟印出評估結果。完成時會清除 checkpoint 並發桌面通知。

---

## 3. 如何使用 AISDLC_Agent

### 3.1 撰寫 Playbook

Playbook 是 AutoClaude 的核心輸入：以 YAML 定義一連串開發任務。放在 `AutoClaude/scripts/` 下。

```yaml
# scripts/my_playbook.yaml
version: "1.0"
project: "MyProject"

# 系統總目標（Gap-011-A）：Minimax 決策對齊 + /compact 後持久注入，防目標漂移
global_goal: |
  建立一個通過所有單元測試的 FastAPI 驗證模組。

# 可選：驅動 AISDLC_SDD 方法論
workflow_type: "aisdlc_sdd"   # auto（預設）/ aisdlc / aisdlc_sdd

global_invariants:
  max_retries_per_step: 3
  auto_compact_interval: 5

tasks:
  - step_id: "T01"
    name: "撰寫測試"
    prompt: |
      請撰寫 tests/test_foo.py，完成後輸出 [TEST_DONE]
    expected_output_regex: "\\[TEST_DONE\\]"
    maintain_context: false

  - step_id: "T02"
    name: "實作並通過測試"
    prompt: |
      請實作 foo.py 通過 tests/test_foo.py，完成後輸出 [TASK_COMPLETE]
    expected_output_regex: "\\[TASK_COMPLETE\\]"
    evaluator_command: "pytest tests/test_foo.py -v"   # 雙重驗證：AI 說完成不算，Evaluator 親跑
    evaluator_timeout_seconds: 60
    maintain_context: true                              # 傳 --continue 維持對話脈絡
```

#### Playbook 欄位速查

**頂層（Playbook）**

| 欄位 | 必填 | 說明 |
|------|------|------|
| `version` / `project` | 是 | 版本與專案名稱 |
| `global_goal` | 否 | 系統總目標，供 Minimax 對齊與 compact anchor |
| `workflow_type` | 否 | `auto` / `aisdlc` / `aisdlc_sdd`（預設 `auto`） |
| `global_invariants` | 否 | `max_retries_per_step`、`auto_compact_interval` |
| `tasks` | 是 | 步驟清單 |

**步驟（PlaybookTask）**

| 欄位 | 預設 | 說明 |
|------|------|------|
| `step_id` / `name` / `prompt` | — | 步驟 ID / 名稱 / 送給 Claude Code 的 prompt |
| `command` | None | 直接執行的 shell 指令（可選） |
| `expected_output_regex` | None | 評估成功的 regex（自動 strip ANSI） |
| `evaluator_command` | None | 額外 shell 評估指令（雙重驗證） |
| `evaluator_timeout_seconds` | 120 | Evaluator 超時秒數 |
| `max_retries` | global | 步驟最大重試次數 |
| `maintain_context` | True | 是否傳 `--continue` 給 Claude Code |

> 完整範本見 [AutoClaude/scripts/example_playbook.yaml](../AutoClaude/scripts/example_playbook.yaml)。

### 3.2 執行與監看

啟動後（見第 2 節）引擎會自動執行。使用期間可觀察：

- **終端輸出**：每步驟的 prompt 分派、Evaluator 結果、Token 用量、修正/演化決策。
- **桌面通知**：ESCALATION（超過重試上限）與最終完成會發桌面通知（需裝 `[notifications]` extra）。
- **logs/**：執行日誌（`config` 的 `log_dir`，預設 `logs/`）。
- **checkpoints/**：斷點續傳檔（`checkpoint_dir`）。

### 3.3 斷點續傳

引擎崩潰或被中斷後，**重新以相同指令啟動即可從上次步驟續跑**（自動讀 checkpoint）；要強制重頭跑才加 `--fresh`。

```bash
# 續傳（預設行為）
python -m autoclaude scripts/my_playbook.yaml --config config.local.yaml
# 放棄 checkpoint 重頭跑
python -m autoclaude scripts/my_playbook.yaml --fresh
```

### 3.4 驅動 AISDLC_SDD 方法論（進階）

將 Playbook 的 `workflow_type` 設為 `aisdlc` 或 `aisdlc_sdd`，AutoClaude 即可驅動 AISDLC_SDD 框架的 SCG-0~6 規格先行閘門流程。框架本身的 Agent / Workflow / 模板使用規則見 [AISDLC_SDD/AISDLC_SDD_v0.01/AISDLC_SDD_INIT.md](../AISDLC_SDD/AISDLC_SDD_v0.01/AISDLC_SDD_INIT.md)。

> SDD 鐵律：`docs_template/sdd/` 模板**不可直接改**，須複製到 `docs/` 對應編號子目錄後再填寫；標 🔴 的人工確認點不可自動跳過。

### 3.5 本機 CI 對等 / Nightly（push 前自我把關，PowerShell）

```powershell
# 在 AutoClaude/ 目錄下
powershell -ExecutionPolicy Bypass -File tools/install_git_hooks.ps1   # 裝 git hooks（commit/push 自動把關）
powershell -ExecutionPolicy Bypass -File tools/local_ci_gate.ps1       # 一鍵本機 CI 閘門（鏡像根層 autoclaude-ci.yml）
powershell -ExecutionPolicy Bypass -File tools/run_local_nightly.ps1   # nightly 6 stage（mutation/pg-e2e/perf/drift/obs）
```

> ⚠️ Nightly 的 perf 階段請用 **Bash 工具/原生終端**啟動，避免某些 PowerShell 載具情境下 perf 數據膨脹的偽陽性。

### 3.6 安全注意事項（使用期間）

- `.env`（含 API Key）與 `config.local.yaml`（含個人路徑）**絕不可 commit**（已 gitignored）。
- `evaluator_command` / `command` 以 `shell=True` 執行，等同信任源 — **勿從不可信來源載入 Playbook**。
- `condition_evaluator` 內建白名單，自動拒絕含 `&&` / `||` / `>` / `<` / 反引號 / `$(...)` 的鏈式指令。

---

## 4. 如何關閉 AISDLC_Agent

AutoClaude 是「跑完即結束」的批次引擎，沒有常駐服務。關閉方式依情境分為三類：

### 4.1 正常結束（自然關閉）

Playbook 全部步驟完成 → 進入 `GOAL_SYNTHESIS` 驗證全局目標 → 清除 checkpoint → 發桌面通知 → **程序自動退出**。無需手動關閉。

### 4.2 執行中安全停止

| 方式 | 操作 | 行為 |
|------|------|------|
| **全域熱鍵** | `ESC + F12` | 安全停止：寫入 checkpoint 後退出，**下次啟動可續傳** |
| **中斷訊號** | `Ctrl + C` | 中止當前程序；已寫入的 checkpoint 仍可續傳 |

> `ESC + F12` 需要 `keyboard` 套件。🔴 **R76 起它已不在 core 依賴裡**（移到選配 extra，成因見
> `AutoClaude/pyproject.toml` 的 `[hotkey]` 段），`bootstrap` 建的環境**預設沒有**它 ⇒ 按了不會有反應，
> 只會在 log 看到一行 warning。要用請顯式安裝：`uv pip install -e 'AutoClaude[hotkey]'`。
> 沒裝（或在非 root 的 macOS 上）就用 `Ctrl + C`——它同樣會寫完 checkpoint 再退出，一樣可續傳。

### 4.3 關閉選配的常駐服務（Docker）

若使用期間啟動過 PostgreSQL / LLM mock / CI 對等容器，需另外關閉：

```bash
# 在 AutoClaude/ 目錄下
docker compose -f docker-compose.ci.yml down        # 關 CI 對等 PG
docker compose -f docker-compose.llm.yml down        # 關本地 LLM/Brain mock
docker compose -f docker-compose.yml down            # 關預設 compose 服務

# 連同資料卷一起清除（⚠️ 會刪除 PG 資料，謹慎使用）
docker compose -f docker-compose.ci.yml down -v
```

### 4.4 移除 git hooks（如需停用本機把關）

`install_git_hooks.{ps1,sh}` 安裝的是根層 dispatcher，設定 `core.hooksPath` 指向 `tools/git-hooks/`（絕對路徑），實際生效的是 **pre-commit / pre-push / post-commit 三支**（post-commit 為 `.git/hooks/post-commit` 委派器，觸發 drift 偵測）。因此**手動移除 `.git/hooks/` 下的檔案沒有用**——那個目錄底下本來就沒有 pre-commit/post-commit（`core.hooksPath` 已經指向別處），閘門實際生效與否只看 `core.hooksPath` 這個 git 設定值。要完全停用，兩支安裝腳本都支援 `--uninstall`（等同 `git config --unset core.hooksPath`，還原成 `.git/hooks` 預設）：

```bash
# macOS / Linux
bash AutoClaude/tools/install_git_hooks.sh --uninstall
```

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File AutoClaude/tools/install_git_hooks.ps1 -Uninstall
```

要重新啟用，再跑一次不帶旗標的安裝指令即可。

### 4.5 完整卸載（清理環境）

```bash
cd AutoClaude
pip uninstall autoclaude            # 移除已安裝套件
deactivate                          # 退出虛擬環境（若用 venv）
# 刪除虛擬環境目錄 .venv/、執行產物 logs/ checkpoints/ backups/（皆可重生）
```

---

## 5. 疑難排解（FAQ）

| 症狀 | 可能原因 | 處置 |
|------|---------|------|
| 啟動即報 `claude` 找不到 | 未安裝 Claude Code CLI 或不在 PATH | 安裝 Claude Code 並確認 `claude --version` 可執行 |
| Minimax 回 `status_code=2049 invalid api key` | API key 與 endpoint 區域不匹配 | 對齊 `.env` 的 `MINIMAX_API_KEY` 與 `MINIMAX_BASE_URL` 區域（國際版 vs 中國版） |
| `alembic upgrade head` 報 `ModuleNotFoundError` | 缺 `psycopg2` | `uv pip install -e '.[postgres]'`（含 psycopg2-binary；venv 若無 pip 模組見上方 1.2 節說明） |
| PG 連線被拒 / TLS 錯誤 | DSN 缺 `?sslmode=require` | 生產加 `?sslmode=require`；本機 dev 可設 `AUTOCLAUDE_ALLOW_INSECURE_DB=1` |
| 回覆語言變成韓/日/簡體 | 長對話語言漂移 | 本專案 Stop hook `check_lang.py` 會 warn；請維持繁體中文 |
| `.sh` 在 bash 噴 `$'\r'` | Windows autocrlf 把行尾轉成 CRLF | `.gitattributes` 已設 `*.sh text eol=lf`；確認檔案為 LF 行尾 |
| Bash 工具呼叫 `tools\xxx.ps1` exit 127 | 反斜線被 escape 吞噬 | 路徑一律用正斜線 `tools/xxx.ps1` |
| 測試/lint 失敗 | 環境未裝齊 | 確認 `uv pip install -e '.[dev,notifications,lint]'` 並用 Python 3.11+ |
| `python -m pip` 報 `No module named pip` | 根層 `.venv` 是 bootstrap 用 uv 建的，內部本來就沒有 pip 模組 | 改用 `uv pip install ...`（見 1.2 節） |

---

## 附錄：權威文件快查

| 主題 | 文件 |
|------|------|
| AutoClaude 開發規範 / 模型欄位 / Architecture Snapshot | [AutoClaude/CLAUDE.md](../AutoClaude/CLAUDE.md) |
| AutoClaude README（快速開始 / Playbook 欄位） | [AutoClaude/README.md](../AutoClaude/README.md) |
| 本機 CI 對等指南 | `AutoClaude/docs/08_deployment/Local_CI_Parity_Guide.md` |
| PostgreSQL 生產切換 SOP | `AutoClaude/docs/08_deployment/DB_Only_Switch_Runbook.md` |
| AISDLC_SDD 框架入口（使用前必讀） | [AISDLC_SDD/AISDLC_SDD_v0.01/AISDLC_SDD_INIT.md](../AISDLC_SDD/AISDLC_SDD_v0.01/AISDLC_SDD_INIT.md) |
| AISDLC_SDD 治理規則總覽 | `AISDLC_SDD/AISDLC_SDD_v0.01/governance/RULES_INDEX.md` |
| monorepo 導航與三條改進軌道 | [CLAUDE.md](../CLAUDE.md) |
</content>
</invoke>
