# AutoClaude 完整使用手冊

> **版本**：0.3.0　｜　**最後更新**：2026-05-14　｜　**平台**：Windows 11 / macOS 13+（主要）/ Linux（次要）；PostgreSQL DB 主機支援 Windows 11

> **適用範圍**：本手冊涵蓋 AutoClaude 唯一現役引擎 — **PlaybookRunner（多步驟狀態機）**。0.2.0 版已下線舊有的單任務 LoopController 模式。

---

## 目錄

1. [專案概覽](#1-專案概覽)
2. [系統需求](#2-系統需求)
3. [安裝指南](#3-安裝指南)
4. [設定檔說明（config.yaml / config.local.yaml）](#4-設定檔說明)
5. [Playbook 撰寫指南（YAML）](#5-playbook-撰寫指南)
6. [狀態機流程詳解](#6-狀態機流程詳解)
7. [執行方式](#7-執行方式)
8. [Minimax 修正大腦](#8-minimax-修正大腦)
9. [Token Guard 與 Checkpoint](#9-token-guard-與-checkpoint)
10. [日誌與通知](#10-日誌與通知)
11. [緊急中斷（ESC+F12）](#11-緊急中斷)
12. [疑難排解](#12-疑難排解)
13. [進階用法](#13-進階用法)
14. [PostgreSQL 後端設定（Phase 6 選配）](#14-postgresql-後端設定)

---

## 1. 專案概覽

AutoClaude 是一套以**狀態機**驅動 Claude Code 的多步驟自動執行引擎，全程對人類操作零干擾。

**核心循環**：感知（PTY 攔截）→ 評估（regex + evaluator）→ 修正（Minimax）→ 重試 / 升級。

```
INIT → CONTEXT_NEGOTIATION → EXECUTE(step N) → EVALUATE
                                                  ↓
                                        ┌─────────┴─────────┐
                                     成功                  失敗
                                        ↓                  ↓
                                    next step         CORRECTION (Minimax)
                                                          ↓
                                                       retry / ESCALATION
                                        ↓
                                       DONE
```

**Token 保護**：context 達 80% 自動 `/compact`、達 90% 儲存 checkpoint 並排程恢復。

---

## 2. 系統需求

| 項目 | 最低版本 | 備註 |
|------|---------|------|
| Python | 3.11+ | 使用了 PEP 604 union types |
| Claude Code CLI | 任一可用版 | 必須能在終端機呼叫 `claude` |
| OS | Windows 11 / macOS 13 / Linux | Windows 主要支援；PostgreSQL DB 主機亦可為 Windows 11 |
| RAM | 4 GB+ | Claude Code 子進程需求 |
| PostgreSQL | 17+（選配） | Phase 6 db_only 模式需求；需安裝 pgvector extension |

---

## 3. 安裝指南

### 3.1 從原始碼安裝

```bash
git clone https://github.com/wuweihungmobile/AutoClaude.git
cd AutoClaude
pip install -e '.[dev,notifications]'
```

### 3.2 設定環境變數

```bash
cp .env.example .env
# 編輯 .env：
# MINIMAX_API_KEY=your_key_here
```

### 3.3 個人化路徑（可選）

```bash
cp config.local.yaml.example config.local.yaml
# 編輯 config.local.yaml，填入工作流程目錄絕對路徑
```

---

## 4. 設定檔說明

### 4.1 主設定 `config.yaml`

```yaml
claude:
  command: claude               # CLI 名稱
  extra_args: []                # 預設不多送旗標（R82 ACB-01：`--yes` 不是 Claude Code 旗標，
                                # 實測 rc=1 `error: unknown option '--yes'`；需免權限提示時改
                                # ["--permission-mode", "bypassPermissions"]）
  continue_flag: "--continue"   # 維持對話脈絡
  encoding: utf-8

minimax:
  api_key: ""                   # 建議用環境變數 MINIMAX_API_KEY
  base_url: "https://api.minimax.io/anthropic"
  model: "MiniMax-M2.7"
  timeout_seconds: 30

loop:
  auth_patterns:
    - "Do you want to proceed\\?"
    - "\\(y/n\\)"
    - "Press Enter to continue"
    - "Allow this action\\?"
  auth_response: "y"
  poll_interval_seconds: 0.2

playbook:
  step_timeout_seconds: 600       # 每步驟最多 10 分鐘
  evaluator_timeout_seconds: 120  # evaluator_command 最多 2 分鐘

token_guard:
  enabled: true
  compact_threshold_pct: 80.0     # 達門檻 → /compact
  halt_threshold_pct: 90.0        # 達門檻 → 儲存 checkpoint
  resume_delay_minutes: 30        # 排程恢復延遲
  auto_resume: true               # 自動恢復
  max_auto_resumes: 10            # 防無限迴圈

notification:
  enabled: true                   # 桌面通知開關

log_dir: logs
backup_dir: backups
checkpoint_dir: checkpoints
scripts_dir: scripts
workflow_search_paths: []         # 個人化路徑請寫入 config.local.yaml
```

### 4.2 個人化覆寫 `config.local.yaml`

不會 commit 進 git，用於存放個人機器絕對路徑：

```yaml
workflow_search_paths:
  - "D:/CursorProject/AISDLC_SDD/AISDLC_SDD_v0.01"
  - "D:/CursorProject/AISDLC/AISDLC_v0.09"
```

執行時：`python -m autoclaude scripts/foo.yaml --config config.local.yaml`

### 4.3 Storage 模式設定（Phase 6 PostgreSQL 選配）

`config.yaml` 或 `config.local.yaml` 中可設定 `storage` 區段：

```yaml
storage:
  mode: "yaml_only"          # yaml_only（預設）/ both（灰度）/ db_only（production）
  db_dsn: ""                 # 建議用環境變數 AUTOCLAUDE_DB_DSN
  dual_write_strict: false   # both 模式：PG 寫入失敗是否 raise
  dual_read_resolution: "yaml_wins"  # yaml_wins / db_wins / fail_loud
```

| 模式 | 行為 | 適用情境 |
|------|------|---------|
| `yaml_only`（預設） | 純 File backend，零 PG 依賴 | 開發 / 單機 |
| `both` | File 主寫 + PG 影子；災難回復 | PG 上線前 ≥ 24h 灰度驗證 |
| `db_only` | 純 PG backend | Production 穩定後 |

> 詳細切換 SOP 見 §14 與 [DB_Only_Switch_Runbook.md](08_deployment/DB_Only_Switch_Runbook.md)。

---

## 5. Playbook 撰寫指南

### 5.1 最小範例

```yaml
version: "1.0"
project: "MyProject"

global_invariants:
  max_retries_per_step: 3
  auto_compact_interval: 5

tasks:
  - step_id: "T01"
    name: "撰寫測試"
    prompt: |
      請撰寫 tests/test_foo.py，完成後輸出 [TEST_DONE]
    expected_output_regex: "\\[TEST_DONE\\]"

  - step_id: "T02"
    name: "實作"
    prompt: |
      請實作 foo.py 通過上述測試，完成後輸出 [TASK_COMPLETE]
    expected_output_regex: "\\[TASK_COMPLETE\\]"
    evaluator_command: "pytest tests/test_foo.py -v"
```

### 5.2 完整欄位定義

#### `Playbook`（根節點）

| 欄位 | 類型 | 預設 | 說明 |
|------|------|------|------|
| `version` | str | "1.0" | Playbook 格式版本 |
| `project` | str | （必填） | 專案名稱 |
| `workflow_type` | str | "auto" | "auto" \| "aisdlc" \| "aisdlc_sdd" |
| `workflow_path` | str? | None | 手動指定工作流程目錄 |
| `global_invariants` | obj | 預設值 | 見下表 |
| `context_negotiation` | obj? | None | 啟動時的初始 prompt 與確認關鍵字 |
| `tasks` | list | （必填） | 步驟陣列 |

#### `GlobalInvariants`

| 欄位 | 類型 | 預設 | 說明 |
|------|------|------|------|
| `max_retries_per_step` | int | 3 | 每步最大重試次數 |
| `auto_compact_interval` | int | 5 | 每 N 步送一次 `/compact`（0 = 停用） |

#### `ContextNegotiation`（可選）

| 欄位 | 類型 | 說明 |
|------|------|------|
| `prompt` | str | 啟動時送出的初始 prompt |
| `expected_keyword` | str | 必須出現在 Claude Code 輸出中才繼續 |

#### `PlaybookTask`

| 欄位 | 類型 | 預設 | 說明 |
|------|------|------|------|
| `step_id` | str | （必填） | 步驟 ID（例如 "T01"） |
| `name` | str | （必填） | 步驟名稱 |
| `prompt` | str | （必填） | 送給 Claude Code 的 prompt |
| `command` | str? | None | Mock CLI 模式使用（生產環境留空） |
| `expected_output_regex` | str? | None | 評估成功的 regex（評估前自動 strip ANSI） |
| `evaluator_command` | str? | None | 額外的 shell 驗證指令 |
| `evaluator_timeout_seconds` | int | 120 | evaluator 最大執行時間 |
| `max_retries` | int? | None | 覆寫此步驟的重試上限 |
| `maintain_context` | bool | true | true=傳遞 `--continue` |

### 5.3 雙重驗證

`expected_output_regex` 比對 Claude Code 的輸出，`evaluator_command` 在子進程中跑你的測試指令。**兩者皆通過才算成功**。AI 嘴巴說完成不算，要由 Evaluator 親自跑 pytest 才算。

---

## 6. 狀態機流程詳解

| 狀態 | 觸發條件 | 行為 |
|------|---------|------|
| INIT | 啟動 | 載入 YAML，偵測工作流程，讀取 checkpoint |
| CONTEXT_NEGOTIATION | playbook 含此欄位且 fresh | 送初始 prompt，等待 `expected_keyword` |
| EXECUTE | 進入步驟 | 啟動 PTY，傳送 prompt，逐行讀取輸出 |
| TOKEN_COMPACT | context >= compact 門檻 | 步驟完成後送 `/compact` |
| TOKEN_HALT | context >= halt 門檻 | 儲存 checkpoint，排程恢復 |
| EVALUATE | 步驟結束 | strip ANSI → regex → evaluator_command |
| CORRECTION | 評估失敗且未達 max_retries | 諮詢 Minimax 取得修正 prompt，重送 |
| ESCALATION | 達到 max_retries | 發桌面通知，回傳 success=False |
| DONE | 全部步驟完成 | 清除 checkpoint，發送完成通知 |

---

## 7. 執行方式

### 7.1 標準執行

```bash
python -m autoclaude scripts/my_playbook.yaml
```

### 7.2 使用個人化設定

```bash
python -m autoclaude scripts/my_playbook.yaml --config config.local.yaml
```

### 7.3 從頭重跑（忽略 checkpoint）

```bash
python -m autoclaude scripts/my_playbook.yaml --fresh
```

### 7.4 退出碼

| 碼 | 意義 |
|----|------|
| 0 | 全部步驟成功完成 |
| 1 | 失敗（Minimax 故障 / max_retries 超限 / token halt 未恢復 / 使用者中斷） |

---

## 8. Minimax 修正大腦

當步驟評估失敗（regex 不符合 / evaluator 失敗），AutoClaude 會將以下資訊送給 Minimax：

```text
## 失敗步驟      T01: 撰寫測試
## 原始 Prompt    （前 800 字）
## 期望 Regex     \[TEST_DONE\]
## 失敗原因      輸出未符合期望 regex
## 評估指令輸出  （後 1500 字）
## 已重試次數    1
```

Minimax 必須回傳 JSON：

```json
{
  "correction_prompt": "...",
  "reasoning": "..."
}
```

`correction_prompt` 會被原樣傳回 Claude Code 做下一輪嘗試。

---

## 9. Token Guard 與 Checkpoint

### 9.1 Context 偵測

從 Claude Code 輸出中以下列 regex 萃取百分比（可自訂）：

```
(\d+(?:\.\d+)?)\s*%\s*(?:context|token)
(?:context|token)\w*[\s:]+(\d+(?:\.\d+)?)\s*%
(\d+)\s*/\s*(\d+)\s*tokens?
\[CONTEXT_USAGE:\s*(\d+(?:\.\d+)?)%\]
```

### 9.2 雙門檻機制

- **80% (compact)**：步驟完成後送 `/compact`，繼續執行下一步
- **90% (halt)**：儲存 checkpoint 並排程恢復，可選擇自動 sleep 或退出

### 9.3 Checkpoint 檔案

位於 `checkpoints/{playbook_stem}.checkpoint.json`，原子寫入（先 .tmp 再 rename）：

```json
{
  "playbook_path": "scripts/foo.yaml",
  "step_idx": 2,
  "step_id": "T03",
  "total_steps": 5,
  "project": "MyProject",
  "completed_step_log": ["[T01] init ✓", "[T02] test ✓"],
  "peak_token_pct": 91.5,
  "saved_at": "2026-04-30T10:30:15",
  "scheduled_resume_at": "2026-04-30T11:00:15"
}
```

---

## 10. 日誌與通知

### 10.1 日誌檔

| 檔案 | 內容 |
|------|------|
| `logs/autoclaude.log` | 主日誌（10 MB rotating，保留 5 份） |
| `logs/playbook_<step>_<attempt>.log` | 每步驟的 PTY 原始輸出 |
| `logs/token_usage.jsonl` | Token 使用記錄（JSONL） |

### 10.2 桌面通知

優先順序：`plyer` → `win10toast` → 寫 log。`config.notification.enabled=false` 可關閉。

通知時機：
- DONE：全部步驟完成
- ESCALATION：達 max_retries 需人工介入
- TOKEN_HALT：context 達限儲存 checkpoint
- AUTO_RESUME：排程中等待恢復

---

## 11. 緊急中斷

按下 `ESC + F12`：

1. 設定全域 `threading.Event`
2. 主迴圈下次檢查時優雅退出
3. 當前步驟 PTY 立即關閉
4. 回傳 `PlaybookResult(success=False, reason="使用者 ESC+F12 中斷")`

需安裝 `keyboard` 套件（已在 dependencies 中）。

---

## 12. 疑難排解

### 12.1 `Minimax API key 未設定`

確認 `.env` 含 `MINIMAX_API_KEY` 或 `config.yaml` 中 `minimax.api_key` 已填。

### 12.2 `Playbook 不是合法格式`

YAML 根節點必須是 dict 且包含 `tasks:` 陣列。0.2.0+ 不再接受舊版單任務格式。

### 12.3 `wexpect 未安裝`

Windows 環境推薦：`pip install wexpect`。缺失時會 fallback 到 subprocess（多數情況可用）。

### 12.4 中文輸出亂碼

確認 `config.yaml` 中 `claude.encoding: utf-8`。Windows PowerShell 可執行 `chcp 65001`。

### 12.5 evaluator_command 永遠失敗

注意：`evaluator_command` 使用 `shell=True` 執行，路徑中有空格時請以引號包覆。**請勿從不可信來源載入 Playbook**。

### 12.6 PostgreSQL 連線問題（Windows DB 主機）

| 症狀 | 原因 | 解決方式 |
|------|------|---------|
| `port 5432 connection refused` | `listen_addresses` 未設 `*` 或防火牆未開放 | 見 §14.3 Step 1~3 |
| `password authentication failed` | pg_hba.conf 未加 192.168.1.25/32 固定 IP 規則 | 見 §14.3 Step 2 |
| `ssl required but not provided` | DSN 缺 sslmode=require 且未設 AUTOCLAUDE_ALLOW_INSECURE_DB | 加環境變數 `AUTOCLAUDE_ALLOW_INSECURE_DB=1` |
| `connect() got unexpected keyword 'sslmode'` | asyncpg 不接受 psycopg2 風格 sslmode 參數 | factory.py 已自動轉換；確認使用最新版 |
| pgvector extension not found | pgvector 未安裝至 Windows PostgreSQL | 見 §14.3 Step 4 |

---

## 13. 進階用法

### 13.1 自訂 context 偵測 regex

`config.yaml` 中 `token_guard.context_patterns` 可加入自己的 pattern。

### 13.2 程式內呼叫

```python
from autoclaude.utils.config import load_config
from autoclaude.decision.minimax_client import MinimaxClient
from autoclaude.perception.hotkey_handler import HotkeyHandler
from autoclaude.execution.playbook_runner import PlaybookRunner

cfg = load_config("config.yaml")
minimax = MinimaxClient(cfg.minimax.api_key, cfg.minimax.base_url, cfg.minimax.model)
hotkey = HotkeyHandler()
runner = PlaybookRunner(cfg, minimax, hotkey, dry_run=False)
result = runner.run("scripts/foo.yaml", fresh=False)
print(result)
```

### 13.3 dry_run 測試模式

```python
runner = PlaybookRunner(cfg, minimax, hotkey, dry_run=True)
```

不會實際呼叫 Claude Code，只以 regex keyword 合成輸出。供單元測試與 Playbook 結構驗證。

### 13.4 Mock CLI 整合測試

```bash
# 啟動模擬 CLI
python tests/fixtures/dummy_cli.py
```

搭配 `tests/fixtures/mock_playbook.yaml` 進行本地端到端測試。

---

---

## 14. PostgreSQL 後端設定（Phase 6 選配）

### 14.1 安裝套件

```bash
# PostgreSQL 核心依賴
pip install 'autoclaude[postgres]'   # SQLAlchemy + asyncpg + alembic + tenacity

# pgvector 向量查詢（選配，需 DB 端安裝 pgvector extension）
pip install 'autoclaude[pgvector]'   # pgvector Python 套件
```

### 14.2 支援平台說明

AutoClaude 同時支援 Windows / macOS / Linux 應用主機，PostgreSQL DB 主機亦支援 Windows 11（如 192.168.1.133）與 Linux。

**Mac 應用端 → Windows DB 主機** 或 **Windows 應用端 → Windows DB 主機** 均可正常運作，`factory.py` 已自動處理 asyncpg sslmode 參數轉換。

### 14.3 Windows 11 PostgreSQL 設定（DB 主機 192.168.1.133）

以下指令均在 **DB 主機（192.168.1.133）** 以 **PowerShell（系統管理員）** 執行。

**Step 1 — 修改 `postgresql.conf`（允許遠端連線）**

```powershell
# 查詢 postgresql.conf 路徑
psql -U postgres -c "SHOW config_file;"

# 以 PowerShell 替換（確認版本號，範例為 17）
$pgConf = "C:\Program Files\PostgreSQL\17\data\postgresql.conf"
(Get-Content $pgConf) `
    -replace "#listen_addresses = 'localhost'", "listen_addresses = '*'" |
    Set-Content $pgConf
```

**Step 2 — 修改 `pg_hba.conf`（允許 LAN 連線）**

```powershell
$pgHba = "C:\Program Files\PostgreSQL\17\data\pg_hba.conf"
Add-Content $pgHba "host    aisdlc    all    192.168.1.25/32    md5"
```

**Step 3 — 重啟服務 + 開放防火牆**

```powershell
# 查詢服務名稱
Get-Service | Where-Object {$_.Name -like "postgresql*"}

# 重啟
$svcName = (Get-Service | Where-Object {$_.Name -like "postgresql*"} | Select-Object -First 1).Name
Restart-Service -Name $svcName

# Windows 防火牆
netsh advfirewall firewall add rule `
    name="PostgreSQL 5432" dir=in action=allow protocol=TCP localport=5432
```

**Step 4 — 安裝 pgvector extension（二選一）**

*方式 A：Docker Desktop（推薦）*

```powershell
docker run -d --name pgvector-db -p 5432:5432 `
    -e POSTGRES_USER=koala `
    -e POSTGRES_PASSWORD=your_password_here `
    -e POSTGRES_DB=aisdlc `
    pgvector/pgvector:pg17
```

*方式 B：原生安裝（無 Docker）*

1. 至 [pgvector Releases](https://github.com/pgvector/pgvector/releases) 下載 Windows 預編譯 zip（對應 PostgreSQL 版本）
2. 以系統管理員複製三個檔案：

```powershell
$pgLib = "C:\Program Files\PostgreSQL\17\lib\"
$pgExt = "C:\Program Files\PostgreSQL\17\share\extension\"
Copy-Item ".\vector.dll"     $pgLib
Copy-Item ".\vector.control" $pgExt
Copy-Item ".\vector--*.sql"  $pgExt
Restart-Service -Name $svcName
```

**Step 5 — 建立 DB / 用戶 / extension**

```sql
-- psql -U postgres
CREATE DATABASE aisdlc;
CREATE USER koala WITH PASSWORD 'your_password_here';
GRANT ALL ON DATABASE aisdlc TO koala;
\c aisdlc
CREATE EXTENSION IF NOT EXISTS vector;
```

**Step 6 — 驗證（從應用主機執行）**

```bash
python -c "
import psycopg2
conn = psycopg2.connect(host='192.168.1.133', dbname='aisdlc', user='koala', password='your_password_here')
cur = conn.cursor()
cur.execute('SELECT version()')
print(cur.fetchone()[0])
cur.execute(\"SELECT extname FROM pg_extension WHERE extname = 'vector'\")
print('pgvector:', cur.fetchone())
conn.close()
print('OK')
"
```

### 14.4 設定灰度驗證（both 模式）

建立 `config.local.yaml`（gitignored）：

```yaml
storage:
  mode: "both"
  db_dsn: "postgresql+asyncpg://koala:your_password_here@192.168.1.133/aisdlc"
  dual_write_strict: true
  dual_read_resolution: "fail_loud"
workflow_search_paths:
  - "D:/CursorProject/AISDLC_SDD/AISDLC_SDD_v0.01"
```

本地網路若無 TLS，設定環境變數暫時跳過：

```bash
# bash / macOS
export AUTOCLAUDE_ALLOW_INSECURE_DB=1

# PowerShell（Windows 應用端）
$env:AUTOCLAUDE_ALLOW_INSECURE_DB = "1"
```

### 14.5 執行 alembic migrations

```bash
export AUTOCLAUDE_MIGRATE_DSN="postgresql://koala:your_password_here@192.168.1.133/aisdlc"
export AUTOCLAUDE_ALLOW_INSECURE_DB=1

alembic upgrade head
alembic current   # 應顯示 0004_pgvector
```

### 14.6 監控 ≥ 24h 灰度驗證

啟動：

```bash
autoclaude <playbook.yaml> --config config.local.yaml
```

每小時確認指標全零：

```python
from autoclaude.infra.repositories.factory import build_state_repository
from autoclaude.utils.config import StorageConfig
repo = build_state_repository(".autoclaude_checkpoints", StorageConfig(mode="both"))
if hasattr(repo, 'metrics'):
    print(repo.metrics.as_dict())
# 通過條件：dual_write_failure=0, shadow_drift_detected=0, shadow_load_failure=0
```

### 14.7 切換 db_only（PM + Stakeholder 簽核後）

```yaml
# config.yaml
storage:
  mode: "db_only"
```

完整 SOP 與回滾方案見 [DB_Only_Switch_Runbook.md](08_deployment/DB_Only_Switch_Runbook.md)。

### 14.8 pgvector 向量查詢（選配）

```python
from autoclaude.infra.repositories.pg_memory_store import PgMemoryStore

store = PgMemoryStore(engine)

# 精確文字匹配（原有功能）
result = store.query("ModuleNotFoundError: No module named 'foo'")

# 語意向量匹配（需先取得 embedding，例如 OpenAI text-embedding-3-small）
# embedding = openai_client.embeddings.create(
#     model="text-embedding-3-small", input="ModuleNotFoundError"
# ).data[0].embedding
# results = store.query_semantic(embedding, top_k=5, threshold=0.8)
```

---

## 變更紀錄

### v0.3.0（2026-05-14）

- Phase 6：PostgreSQL 後端正式上線（yaml_only / both / db_only 三段開關）
- 新增 pgvector 向量查詢支援（knowledge_entries embedding 欄 + HNSW index）
- factory.py：修復 asyncpg sslmode 參數相容性（`_normalize_asyncpg_dsn`）
- 新增 §14 PostgreSQL 後端設定（含 Windows 11 DB 主機完整步驟）
- 測試基線：1034 passed / 10 skipped

### v0.2.0（2026-04-30）

- 下線 LoopController 單任務模式（YAML 不含 `tasks:` 將直接報錯）
- 抽出 `perception/text_utils.py` 統一管理 strip_ansi
- `notifier` 支援 `enabled` 開關，尊重 `config.notification.enabled`
- `config.yaml` 移除絕對路徑，改以 `config.local.yaml` 個人化覆寫
- 新增根層 `README.md`
- 整理測試結構，依模組拆分

### v0.1.0

- 初版 PlaybookRunner 狀態機
- Token Guard 雙門檻 + Checkpoint 斷點續傳
- AISDLC / AISDLC_SDD 工作流程偵測
