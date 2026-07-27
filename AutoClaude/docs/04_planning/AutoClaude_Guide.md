# AutoClaude 完整使用與架構手冊

> **手冊版本**：1.1.0　｜　**最後更新**：2026-06-13　｜　**對應里程碑**：AutoClaude_Improving_012 Phase 1（記憶基座）
> **套件版本**（`pyproject.toml`）：0.1.0　｜　**測試基線**：2,931 passed / 122 skipped（2026-06-13 實測，pytest-randomly 未啟用，順序由 collection 確定）
> **平台**：Windows 11（主要）/ macOS 13+ / Linux（次要）；PostgreSQL DB 主機支援 Windows 11 與 Linux

> **適用範圍**：本手冊涵蓋 AutoClaude 唯一現役引擎 — **微核心化 PlaybookKernel（多步驟 DAG 狀態機）**。
> 0.2.0 版已下線舊有的單任務 LoopController；SD_05 W6 已物理拔除舊 `PlaybookRunner` 直連模式，**Kernel 路徑為唯一正式路徑**（`PlaybookRunner` 僅保留為 thin facade）。

---

## 目錄

1. [專案概覽](#1-專案概覽)
2. [微核心架構（core / infra / plugins / ports）](#2-微核心架構)
3. [系統需求](#3-系統需求)
4. [安裝指南](#4-安裝指南)
5. [設定檔說明（config.yaml / config.local.yaml）](#5-設定檔說明)
6. [Playbook 撰寫指南（YAML）](#6-playbook-撰寫指南)
7. [執行流程與狀態機](#7-執行流程與狀態機)
8. [執行方式（CLI / 程式內呼叫）](#8-執行方式)
9. [Minimax 修正大腦](#9-minimax-修正大腦)
10. [Token Guard 與 Checkpoint](#10-token-guard-與-checkpoint)
11. [動態突變與自演化（Level 5 自治）](#11-動態突變與自演化)
12. [可觀測性（IObservabilityPort / trace_id）](#12-可觀測性)
13. [日誌與通知](#13-日誌與通知)
14. [緊急中斷（ESC+F12）](#14-緊急中斷)
15. [PostgreSQL 後端設定（DAL 三後端）](#15-postgresql-後端設定)
16. [品質與工程治理（LOC / importlinter / mutation / perf / nightly）](#16-品質與工程治理)
17. [疑難排解](#17-疑難排解)
18. [進階用法](#18-進階用法)
19. [變更紀錄](#19-變更紀錄)

---

## 1. 專案概覽

AutoClaude 是一套以**狀態機**驅動 Claude Code CLI 的多步驟自動執行引擎，全程對人類操作零干擾，定位為 **Level 5 自治系統**（動態突變 + 自演化 + 目標對齊 + 跨 Session 持久化 + 元學習閉環）。

**核心循環**：感知（PTY 攔截）→ 評估（regex + evaluator）→ 修正（Minimax）→ 重試 / 突變 / 升級 / 演化。

```
INIT → CONTEXT_NEGOTIATION → EXECUTE(step N) → EVALUATE
                                                  │
                                        ┌─────────┴─────────┐
                                     成功                  失敗
                                        │                  │
                                    next step      CORRECTION（Minimax）
                                        │                  │
                                        │          retry / 動態突變
                                        │                  │
                                        │          達 max_retries → ESCALATION
                                        │                  │
                                        │          PlaybookEvolver 嘗試自演化
                                        ▼
                                       DONE（goal_synthesis 全局目標驗證）
```

**Token 保護**：context 達 80% 於步驟完成後自動 `/compact`；達 90% 儲存 checkpoint 並排程恢復。

**架構演進（Phase 0~6 / SD_03~SD_09）**：

| 階段 | 重點 |
|------|------|
| Phase 0~3 | baseline + `core/`（Kernel + EventBus + HookSpec + Ports）+ `infra/`（adapters + repositories）+ 12 Plugin 拆解 |
| Phase 4~6 | PlaybookRunner thin facade（Kernel facade）+ DAL 抽象化（File / InMemory / PG 三後端）+ pgvector HNSW（m=16, ef_construction=64）|
| SD_03~06 | Facade 切換 / god-object 拆解 / Counter SSOT + TokenGuard 下沉 + Mutation v2 / PG 三層任務模型 + Brain·Executor 分工 |
| SD_07 | ADR-SD07-001 LOC 分級政策；肥胖檔案二度拆解；6 大議題 e2e；PlaybookResult → KernelResult 物理拔除 |
| SD_08 | 文件治理（CLAUDE.md ≤ 400）+ 可觀測性（IObservabilityPort）+ mutation/perf baseline + 5 條 ADR |
| SD_09 | PG production SOP 落地評估 + 三個觀察期本地 nightly 採集 + W3 zero-trust audit 連 38 輪（R24~R61）|
| Improving_012 | Agentic 三大能力 gap 分析（SCG-0 凍結）+ Phase 1 記憶基座（F-C3/F-C1/F-C2，2026-06-13）|

> 完整 Sprint 脈絡見 [sprint_history.md](../05_development/sprint_history.md)；架構決策見 [ADR/](ADR/)（SD06~SD09 共 17 條）。

---

## 2. 微核心架構

AutoClaude 採 **Hexagonal Architecture（六角架構）**：核心領域（Kernel）不依賴具體基礎設施，所有外部互動透過 **12 個 Port（介面）** 與 **EventBus** 解耦；具體實作為 **infra adapters**，可變行為由 **plugins** 透過 hook 注入。

```
autoclaude/
├── main.py / __main__.py           # CLI 入口 + Playbook 格式驗證
├── core/                            # 微核心層（不得 import execution / infra）
│   ├── kernel.py                   # PlaybookKernel 純粹 DAG 狀態機（≤ 250 行）
│   ├── kernel_state.py             # KernelResult（SSOT，取代 PlaybookResult）
│   ├── event_bus.py / hookspec.py / wiring.py
│   ├── orchestration/              # OrchestrationCoordinator（SD_06 W1）
│   ├── ports/                      # 12 ports（見下表）
│   └── services/                   # mutation/ + auto_resume.py + _auto_resume_metrics.py
├── infra/                           # 基礎設施層
│   ├── adapters/                   # MinimaxBrain / PtyExecutor / ShellEvaluator / observability/
│   └── repositories/               # factory.py + 3 後端（File / InMemory / PG）+ Dual
├── plugins/                         # 16 active / 17 靜態（hotkey 條件式註冊）
├── models/                          # Playbook / Decision / Escalation / StepMutation
├── perception/                      # PTY wrapper / StreamReader / hotkey
├── decision/                        # MinimaxClient / PromptBuilder
├── execution/                       # playbook_runner（thin facade）/ steps_orchestrator/ /
│                                    # workflow_detector / failure_tracker / convergence_monitor /
│                                    # error_classifier / error_budget / cross_step_validator
├── evolution/                       # PlaybookEvolver（INJECT_STEP / SPLIT_STEP）
└── utils/                           # config / logger / notifier / checkpoint_manager /
                                     # token_tracker / knowledge_base / trace_context
```

### 2.1 12 個 Port（`autoclaude/core/ports/`）

| Port | 職責 | 預設 adapter |
|------|------|--------------|
| `brain` | 失敗修正決策（Minimax）| `MinimaxBrain` |
| `executor` | 執行 prompt 並回傳輸出（PTY/subprocess）| `PtyExecutor` |
| `evaluator` | 跑 evaluator_command 驗證 | `ShellEvaluator` |
| `memory_store` | 失敗知識庫（meta-learning）| File / `PgMemoryStore` |
| `playbook_repository` | Playbook 載入/儲存 | File / PG |
| `state_repository` | Checkpoint 持久化 | File / InMemory / PG / Dual |
| `embedder` | 文字向量化（pgvector 選配）| — |
| `vector_search` | 語意檢索（HNSW）| `PgMemoryStore` |
| `observability` | 結構化 metric / log（SD_08 W4）| `LocalLogger` / `NullObservability` |
| `spec_source` | SDD 規格來源 → Playbook（AutoSDD W1）| `SddToPlaybookAdapter` |
| `kb_metric_store` | KB metrics 跨 session 持久化（F-C3，ADR-SD09-006）| `LocalKbMetricStore`（jsonl）/ `PgKbMetricStore` |
| `preference_store` | 使用者偏好記憶（F-C1，ADR-AGT-003）| `FilePreferenceStore` / `PgPreferenceStore` |

### 2.2 16 個 Plugin（按 `wiring._REGISTER_ORDER`）

`pre_run_validator` → `hotkey` → `cross_step_validator` → `token_guard` → `global_goal_anchor` → `playbook_persistence` → `sdd_governance` → `fast_path` → `notification` → `knowledge_base` → `preference_memory` → `goal_synthesis` → `goal_progress` → `convergence` → `evolution` → `goto_counter` → `checkpoint`（17 靜態含條件式註冊的 hotkey）。

**Plugin 鐵律**（由 `.importlinter` 強制）：Plugin 之間**不可互相 import**，協作一律走 EventBus；Plugin 不得直接 import infra 或 `utils.observability` helpers（須走 `IObservabilityPort`）；Plugin 不得直接 import `IKbMetricStore`（須走 FailureKnowledgeBase routing，Rule 8）。

### 2.3 新增 Plugin 的 SOP

1. 建立 `autoclaude/plugins/<feature>_plugin.py`（PascalCase 類別名）
2. 繼承 `HookSpec`，實作對應 hook（`before_step` / `after_step` / `on_token_halt` / `on_escalation` 等）
3. 註冊至 `wiring._REGISTER_ORDER`，依需要 constructor 注入 ports（**不可直接 import infra**）
4. 撰寫單元測試 `tests/plugins/test_<feature>.py`，目標 coverage ≥ 90%
5. LOC 預算分級（ADR-SD07-001）：plugin_entry ≤ 250；超出拆 `<feature>_plugin/` package
6. 禁止反向相依：協作走 EventBus（`.importlinter` Rule 1 阻擋）

---

## 3. 系統需求

| 項目 | 最低版本 | 備註 |
|------|---------|------|
| Python | 3.11+ | 使用 PEP 604 union types |
| Claude Code CLI | 任一可用版 | 必須能在終端機呼叫 `claude` |
| OS | Windows 11 / macOS 13 / Linux | Windows 主要支援 |
| RAM | 4 GB+ | Claude Code 子進程需求 |
| PostgreSQL | 17+（選配） | `db_only` / `both` 模式需求；需 pgvector extension |
| Docker Desktop | 選配 | 本地 pg17 / mutation nightly / act CI 對等 |

---

## 4. 安裝指南

### 4.1 從原始碼安裝

```bash
git clone https://github.com/wuweihungmobile/AutoClaude.git
cd AutoClaude
pip install -e '.[dev,notifications]'
```

選配相依群組（`pyproject.toml [project.optional-dependencies]`）：

| Extra | 內容 | 用途 |
|-------|------|------|
| `notifications` | plyer / win10toast | 桌面通知 |
| `postgres` | SQLAlchemy + asyncpg + alembic + tenacity | PG 後端（`both` / `db_only`）|
| `pgvector` | pgvector ≥ 0.3 | 語意向量查詢（需 DB 端 extension）|
| `dev` | pytest 等 | 開發 / 測試 |

### 4.2 設定環境變數

```bash
cp .env.example .env
# 編輯 .env：
# MINIMAX_API_KEY=your_key_here
# （選配）MINIMAX_BASE_URL / MINIMAX_MODEL：可把 Brain 指向本機 OpenAI 相容端點（mock_brain_server / vLLM）
```

### 4.3 個人化路徑（可選）

```bash
cp config.local.yaml.example config.local.yaml
# 編輯 config.local.yaml，填入工作流程目錄絕對路徑（不會 commit 進 git）
```

---

## 5. 設定檔說明

### 5.1 主設定 `config.yaml`（對齊 `autoclaude/utils/config.py`）

```yaml
claude:
  command: claude                 # CLI 名稱
  extra_args: ["--yes"]           # 預設旗標
  continue_flag: "--continue"     # 維持對話脈絡
  encoding: utf-8

minimax:
  api_key: ""                     # 建議用環境變數 MINIMAX_API_KEY
  base_url: "https://api.minimax.chat/v1/text/chatcompletion_v2"  # 可被 MINIMAX_BASE_URL 覆寫
  model: "MiniMax-Text-01"        # 可被 MINIMAX_MODEL 覆寫
  timeout_seconds: 30

loop:
  max_iterations: 20
  completion_pattern: "執行完畢[,，]\\s*報告如下"
  auth_patterns:
    - "Do you want to proceed\\?"
    - "\\(y/n\\)"
    - "Press Enter to continue"
    - "Allow this action\\?"
  auth_response: "y\n"
  poll_interval_seconds: 0.2

playbook:
  step_timeout_seconds: 600              # 每步驟最多 10 分鐘
  evaluator_timeout_seconds: 120         # evaluator_command 最多 2 分鐘
  global_goal_anchor_chars: 400          # Gap-013-H：/compact MEMORY ANCHOR 中 [GLOBAL_GOAL] 字元數（100~1000）
  max_evolutions: 3                      # Gap-020：自動演化最大次數（1~10）
  goal_synthesis_enabled: true           # Gap-014：DONE 前全局目標驗證
  global_goal_brief_chars: 150           # Gap-015：非首步精簡 global_goal 字元數（50~500）
  conditional_evaluator_timeout_seconds: 5   # Gap-038：CONDITIONAL 突變 condition_evaluator 超時
  max_goto_per_step: 3                   # Gap-049：GOTO_STEP 每目標步驟最大跳轉次數

token_guard:
  enabled: true
  compact_threshold_pct: 80.0     # 達門檻 → /compact（必須 < halt_threshold_pct）
  halt_threshold_pct: 90.0        # 達門檻 → 儲存 checkpoint
  resume_delay_minutes: 30        # 排程恢復延遲（0~1440）
  auto_resume: true               # 自動恢復
  max_auto_resumes: 10            # 防無限迴圈（1~100）
  # context_patterns: 7 個內建 regex（含 Context window / [STATS: usage N%] / Token usage: N tokens / max M）

notification:
  enabled: true                   # 桌面通知開關
  webhook_url: null               # 可選 webhook

storage:
  mode: "yaml_only"               # yaml_only（預設）/ both（灰度）/ db_only（production）
  db_dsn: null                    # 建議用環境變數 AUTOCLAUDE_DB_DSN
  dual_write_strict: false        # both 模式：PG 寫入失敗是否阻斷主寫
  dual_read_resolution: "yaml_wins"   # yaml_wins / db_wins / fail_loud

log_dir: logs
backup_dir: backups
scripts_dir: scripts
checkpoint_dir: checkpoints
workflow_search_paths: []         # 個人化路徑請寫入 config.local.yaml
```

> **內建防呆**（pydantic validator）：`halt_threshold_pct` 必須 > `compact_threshold_pct`；`context_patterns` 每項須為合法 regex（以 `re.IGNORECASE` 編譯）；`storage.mode` 為 `both`/`db_only` 時必須提供 `db_dsn` 或環境變數。

### 5.2 個人化覆寫 `config.local.yaml`（gitignored）

```yaml
workflow_search_paths:
  - "D:/CursorProject/AISDLC_SDD/AISDLC_SDD_v0.01"
  - "D:/CursorProject/AISDLC/AISDLC_v0.09"
```

執行：`python -m autoclaude scripts/foo.yaml --config config.local.yaml`

### 5.3 環境變數覆寫優先序

| 設定 | 優先序 |
|------|--------|
| Minimax API key | `MINIMAX_API_KEY` > `config.minimax.api_key` |
| Brain base_url | `MINIMAX_BASE_URL` > `config.minimax.base_url` |
| Brain model | `MINIMAX_MODEL` > `config.minimax.model` |
| PG DSN | `AUTOCLAUDE_DB_DSN` > `AUTOCLAUDE_PG_DSN`（deprecated）> `config.storage.db_dsn` |

---

## 6. Playbook 撰寫指南

### 6.1 最小範例

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

### 6.2 完整欄位定義（對齊 `autoclaude/models/playbook.py`）

#### `Playbook`（根節點）

| 欄位 | 類型 | 預設 | 說明 |
|------|------|------|------|
| `version` | str | "1.0" | Playbook 格式版本 |
| `project` | str | （必填） | 專案名稱 |
| `global_goal` | str? | None | **Gap-011-A**：自治系統總目標，供 Minimax 修正決策對齊 |
| `workflow_type` | str | "auto" | "auto" \| "aisdlc" \| "aisdlc_sdd" |
| `workflow_path` | str? | None | 手動指定工作流程目錄 |
| `global_invariants` | obj | 預設值 | 見下表 |
| `context_negotiation` | obj? | None | 啟動時的初始 prompt 與確認關鍵字 |
| `evolution_metadata` | obj? | None | **Gap-024-A**：演化版 Playbook 元資料（重載後恢復 mutation_log）|
| `tasks` | list | （必填） | 步驟陣列 |

#### `GlobalInvariants`

| 欄位 | 類型 | 預設 | 說明 |
|------|------|------|------|
| `max_retries_per_step` | int | 3 | 每步最大重試次數 |
| `auto_compact_interval` | int | 5 | 每 N 步送一次 `/compact`（0 = 停用）|

#### `PlaybookTask`

| 欄位 | 類型 | 預設 | 說明 |
|------|------|------|------|
| `step_id` | str | （必填） | 步驟 ID（例如 "T01"）|
| `name` | str | （必填） | 步驟名稱 |
| `prompt` | str | （必填） | 送給 Claude Code 的 prompt |
| `command` | str? | None | Mock CLI 模式使用（生產環境留空）|
| `expected_output_regex` | str? | None | 評估成功的 regex（評估前自動 strip ANSI）|
| `evaluator_command` | str? | None | 額外的 shell 驗證指令 |
| `evaluator_timeout_seconds` | int | 120 | evaluator 最大執行時間 |
| `max_retries` | int? | None | 覆寫此步驟的重試上限 |
| `maintain_context` | bool | true | true = 傳遞 `--continue` |
| `token_guard` | dict? | None | **SD_05 W2**：per-step token_guard override（合法欄位由 `TokenGuardConfig` 白名單驗證，攔截 typo）|

### 6.3 雙重驗證

`expected_output_regex` 比對 Claude Code 的輸出，`evaluator_command` 在子進程中跑你的測試指令。**兩者皆通過才算成功**。AI 嘴巴說完成不算，要由 Evaluator 親自跑 pytest 才算。

> 完整範例見 [scripts/example_playbook.yaml](../../scripts/example_playbook.yaml)（AISDLC_SDD Auth Module TDD 循環，含 `global_goal` 與 evaluator）。

---

## 7. 執行流程與狀態機

| 狀態 | 觸發條件 | 行為 |
|------|---------|------|
| INIT | 啟動 | 載入 YAML，偵測工作流程，讀取 checkpoint |
| CONTEXT_NEGOTIATION | playbook 含此欄位且 fresh | 送初始 prompt，等待 `expected_keyword` |
| EXECUTE | 進入步驟 | 啟動 PTY，傳送 prompt，逐行讀取輸出 |
| TOKEN_COMPACT | context ≥ compact 門檻 | 步驟完成後送 `/compact`（含 MEMORY ANCHOR）|
| TOKEN_HALT | context ≥ halt 門檻 | 儲存 checkpoint，排程恢復 |
| EVALUATE | 步驟結束 | strip ANSI → regex → evaluator_command |
| CORRECTION | 評估失敗且未達 max_retries | 諮詢 Minimax 取得修正 prompt / 突變，重送 |
| ESCALATION | 達到 max_retries | 桌面通知 + `EscalationDump` + `PlaybookEvolver` 自動演化 |
| DONE | 全部步驟完成 | goal_synthesis 全局目標驗證 → 清除 checkpoint，發送完成通知 |

**KernelResult（SSOT，取代 PlaybookResult）**：`success` / `completed_steps` / `total_steps` / `reason` / `step_log` / `completed_step_ids` / `workflow` / `halted`（含 `halt_for_token` property alias）/ `scheduled_resume_at` / `evolved_playbook_path` / `evolution_fresh_required`。建構走 factory：`succeeded()` / `escalated_()` / `halted_()` / `vetoed()`。

---

## 8. 執行方式

### 8.1 CLI

```bash
# 標準執行
python -m autoclaude scripts/my_playbook.yaml

# 使用個人化設定
python -m autoclaude scripts/my_playbook.yaml --config config.local.yaml

# 從頭重跑（忽略 checkpoint）
python -m autoclaude scripts/my_playbook.yaml --fresh

# 安裝為 console script 後
autoclaude scripts/my_playbook.yaml --config config.local.yaml
```

### 8.2 退出碼

| 碼 | 意義 |
|----|------|
| 0 | 全部步驟成功完成（`result.success == True`）|
| 1 | 失敗（Minimax 故障 / max_retries 超限 / token halt 未恢復 / 使用者中斷 / Playbook 格式錯誤）|

### 8.3 程式內呼叫（微核心組裝）

`main.py` 的組裝流程為 build adapters → `build_kernel` → `AutoResumeService.run`：

```python
from autoclaude.utils.config import load_config
from autoclaude.perception.hotkey_handler import HotkeyHandler
from autoclaude.decision.minimax_client import MinimaxClient
from autoclaude.core.wiring import build_kernel
from autoclaude.core.services.auto_resume import AutoResumeService
from autoclaude.infra.adapters.pty_executor import PtyExecutor
from autoclaude.infra.adapters.shell_evaluator import ShellEvaluator
from autoclaude.infra.repositories import build_state_repository

cfg = load_config("config.yaml")
minimax = MinimaxClient(cfg.minimax.api_key, cfg.minimax.base_url,
                        cfg.minimax.model, timeout=cfg.minimax.timeout_seconds)
hotkey = HotkeyHandler()

executor = PtyExecutor(cfg)
evaluator = ShellEvaluator(cfg.playbook)
state_repo = build_state_repository(cfg.checkpoint_dir, cfg.storage)
kernel = build_kernel(cfg, executor=executor, evaluator=evaluator,
                      hotkey=hotkey, minimax_client=minimax,
                      state_repository=state_repo)
service = AutoResumeService(kernel, cfg, state_repository=state_repo)
result = service.run("scripts/foo.yaml", fresh=False)
print(result.success, result.completed_steps, "/", result.total_steps)
```

> `PlaybookRunner` 仍以 thin facade 形式存在（`autoclaude/execution/playbook_runner.py`），內部委派 Kernel；新程式碼建議直接使用 `build_kernel` + `AutoResumeService`。

---

## 9. Minimax 修正大腦

當步驟評估失敗（regex 不符 / evaluator 失敗），AutoClaude 將以下資訊送給 Minimax（透過 `IBrain` port）：

```text
## 失敗步驟      T01: 撰寫測試
## 原始 Prompt    （前 800 字）
## 期望 Regex     \[TEST_DONE\]
## 失敗原因      輸出未符合期望 regex
## 評估指令輸出  （後 1500 字）
## 已重試次數    1
## 系統總目標    （若 Playbook 設定 global_goal，Gap-011-A 注入此段供對齊）
```

Minimax 必須回傳 JSON：

```json
{
  "correction_prompt": "...",
  "reasoning": "..."
}
```

`correction_prompt` 經 **Hallucination Guard**（驗證長度、與上次相似度、具體錯誤引用）後原樣傳回 Claude Code 做下一輪嘗試。

**本機 mock Brain**：設定 `MINIMAX_BASE_URL` 指向 `tools/mock_brain_server.py`（OpenAI 相容端點），可在無真實 API key 下做本地端到端測試。

---

## 10. Token Guard 與 Checkpoint

### 10.1 Context 偵測

從 Claude Code 輸出以 7 個內建 regex（`token_guard.context_patterns`）萃取百分比，涵蓋 `%context`、`context%`、`N/M tokens`、`[CONTEXT_USAGE: N%]`、`Context window: N / M tokens`、`[STATS: usage N%]`、`Token usage: N tokens / max M`。

### 10.2 雙門檻機制

- **80%（compact）**：步驟完成後送 `/compact`，並注入 MEMORY ANCHOR（`[GLOBAL_GOAL]` + `[ACTIVE_TASK]` + `[SUCCESS_CONDITION]`，Evo-006 Gap-039），杜絕壓縮失憶導致的目標漂移。
- **90%（halt）**：儲存 checkpoint 並排程恢復；`auto_resume=true` 等待 `resume_delay_minutes` 後自動續跑，`false` 則退出由人類決定。

### 10.3 PlaybookCheckpoint（`autoclaude/utils/checkpoint_manager.py`）

跨 TOKEN_HALT / ESC+F12 / 演化重啟的執行狀態持久化，**原子寫入**（先 `.tmp` 再 rename）。核心欄位：

`playbook_path` / `step_idx` / `step_id` / `total_steps` / `peak_token_pct` / `scheduled_resume_at` / `failure_history`（Gap-007-A）/ `active_step_attempt` / `last_correction_prompt` / `completed_step_ids`（Gap-041/042）/ `goto_counter` / `inject_before_counter` / `skip_to_counter` / `step_evolution_counter`（Gap-042/048，跨 Session 防無限迴圈）/ `run_id` / `goal_task_id`（SD_06 W5，三層任務模型）。

> 4 個 counter 寫入 checkpoint、啟動時自動恢復，是「跨 Session 防無限迴圈」的關鍵（Gap-042/048）。

---

## 11. 動態突變與自演化

Level 5 自治的核心：失敗不只重試，還能**改寫步驟序列**與**自我演化**。

### 11.1 動態步驟突變（Gap-011-B / Evo-005）

觸發門檻：`attempt ≥ 2 && convergence_trend in (stuck / oscillating / cycling)`。Minimax 可提議 7 種突變類型，並支援 `batch_mutations`（最多 3 個原子序列）：

| 突變 | 行為 |
|------|------|
| `REVISE_CURRENT` | 改寫當前步驟 prompt |
| `INJECT_AFTER` / `INJECT_BEFORE` | 在前/後注入新步驟 |
| `GOTO_STEP` | 跳回先前步驟（`max_goto_per_step` 上限，Gap-049）|
| `DELETE_STEP` | 刪除步驟 |
| `SKIP_TO` | 跳至指定步驟 |
| `CONDITIONAL` | 依 `condition_evaluator` 結果分支（Gap-038）|

### 11.2 自演化引擎（`autoclaude/evolution/`）

- **MinimaxEvolver（AI 驅動）**：ESCALATION 時諮詢 Minimax 提議語意正確的演化策略（INJECT_STEP / SPLIT_STEP / REVISE_EVALUATOR）。
- **PlaybookEvolver（規則兜底）**：AI 失敗時退回規則引擎，基於失敗模式注入前置步驟或拆分複雜步驟。
- **跨步驟模式分析（Gap-033）**：多步同類型錯誤（import / environment）→ 自動注入全域環境初始化步驟。
- **演化效率（Evo-006 Gap-041）**：演化後從最後成功步驟恢復（透過 `completed_step_ids`），不再強制 fresh 全重跑。
- **per-step 演化次數（Evo-006 Gap-048）**：同一步驟最多演化 2 次，防單步消耗所有配額（`max_evolutions` 全域上限 3）。
- **KB 預播種兜底（Gap-045）**：演化後重啟以 `{ErrorClass.IMPORT}:{_PRE_id}:env_setup` 預播種；查詢端主 key 未中時回退兜底 key。

### 11.3 防護機制

- **ErrorBudget**：per-error-class 重試上限（syntax:2, assertion:5, environment:0）。
- **CrossStepValidator**：步驟切換前以 `git status` 偵測污染（> 5 個修改未確認時警告）。
- **Meta-learning（FailureKnowledgeBase）**：跨 session 記錄成功策略（透過 `memory_store` port）。

### 11.4 記憶基座（Improving_012 Phase 1）

2026-06-13 落地的三項跨 session 記憶能力（經 SCG-1/SCG-2 人工確認）：

- **F-C3 KB metrics 跨 session 持久化**（`kb_metric_store` port，ADR-SD09-006）：KB metric 重啟不清零；`yaml_only` 模式寫 `.kb_metrics_local.jsonl`，`both` / `db_only` 模式寫 `kb_metrics` 表；於 POST_RUN flush。
- **F-C1 使用者偏好**（`preference_memory` plugin + `preference_store` port，ADR-AGT-003）：偏好存於 `preferences.jsonl` / `user_preferences` 表；`config.yaml` 可選 `preferences:` 區段做 seed；PRE_CORRECTION 時將偏好注入 correction prompt 的 `## 使用者偏好` 區段（上限 10 鍵）。
- **F-C2 GoalProgressLedger**（`goal_progress` plugin）：進度存於 `goal_progress.jsonl` / `goal_progress` 表；POST_RUN 記錄當次結果，`goal_task_id` 缺漏時以 `project:{name}` fallback；`summarize()` 提供跨 run 彙總。

> 規格與決策詳見 [SRD_AGT_Phase1_Memory.md](../02_architecture/SRD_AGT_Phase1_Memory.md)、[ADR-AGT-003-memory-layering.md](ADR/ADR-AGT-003-memory-layering.md)、[AutoClaude_Improving_012.md](AutoClaude_Improving_012.md)。

---

## 12. 可觀測性

SD_08 W4 落地 **IObservabilityPort**（ADR-SD08-004），核心領域不依賴具體 logger 實作：

- **adapter**：`LocalLogger`（結構化 JSON log）/ `NullObservability`（未注入時 fallback，避免 None check 散落）。
- **trace_id**：`utils/trace_context.py` 以 `ContextVar` 傳遞 trace_id，跨步驟串接（ADR-SD09-004 支援多進程）。
- **KB metric 4 項**：knowledge_base 命中/未命中/預播種/回退兜底等指標（Improving_012 Phase 1 起跨 session 持久化，見 §11.4 F-C3）。
- **Plugin 約束**（importlinter Rule 7）：Plugin 不得直接 import `utils.observability` helpers，須走 `IObservabilityPort`。

Kernel 透過 `kernel.observability` property 對外暴露，供 Coordinator / AutoResume 讀取。

---

## 13. 日誌與通知

### 13.1 日誌檔

| 檔案 | 內容 |
|------|------|
| `logs/autoclaude.log` | 主日誌（rotating）|
| `logs/playbook_<step>_<attempt>.log` | 每步驟的 PTY 原始輸出 |
| `logs/token_usage.jsonl` | Token 使用記錄（JSONL）|
| `logs/nightly_latest.log` | nightly 單一真相 log（取證紀律 #3，PASS 聲稱須引 RunId log:L 行號）|

### 13.2 桌面通知

優先順序：`plyer` → `win10toast` → 寫 log。`config.notification.enabled=false` 可關閉。通知時機：DONE / ESCALATION / TOKEN_HALT / AUTO_RESUME。

---

## 14. 緊急中斷

按下 `ESC + F12`：

1. 設定全域 `threading.Event`
2. 主迴圈下次檢查時優雅退出
3. 當前步驟 PTY 立即關閉
4. 回傳 `KernelResult(success=False, reason="使用者 ESC+F12 中斷")`

需安裝 `keyboard` 套件（已在 dependencies 中）。HotkeyPlugin 為條件式註冊（無互動終端時跳過）。

---

## 15. PostgreSQL 後端設定

### 15.1 DAL 三後端 `storage.mode`（`autoclaude/infra/repositories/factory.py`）

| 模式 | 行為 | 適用 |
|------|------|------|
| `yaml_only`（預設）| `FileStateRepository`（單一；零 PG 依賴）| 開發 / 單機 |
| `both` | `DualStateRepository`（File 主寫 + PG 影子；`fail_loud` / `yaml_wins` / `db_wins`）| PG 上線灰度 |
| `db_only` | `PgStateRepository`（單一；YAML 僅供匯入）| Production 穩定後 |

DSN 解析優先級：`AUTOCLAUDE_DB_DSN` > `AUTOCLAUDE_PG_DSN`（deprecated）> `config.storage.db_dsn`。

> **⛔ Production 上線紅線（SD_06 遺留）**：真正上線前必須由人類 DBA 在公司 staging（≥ 1M 真實列）重跑 + 人類 PM 親簽 release approval。SD_08 W5 落地 ADR-SD08-005 雙軌制 + `pg_health.py` WAL lag adapter；正式啟用雙條件 — 可觀測性 GA + 30 天零 drift（SD_09 觀察期採集中）。

### 15.2 安裝套件

```bash
pip install autoclaude[postgres]   # SQLAlchemy + asyncpg + alembic + tenacity
pip install autoclaude[pgvector]   # pgvector Python 套件（需 DB 端安裝 extension）
```

### 15.3 Windows 11 PostgreSQL DB 主機設定（以系統管理員 PowerShell 於 DB 主機執行）

**Step 1 — `postgresql.conf` 允許遠端連線**

```powershell
psql -U postgres -c "SHOW config_file;"
$pgConf = "C:\Program Files\PostgreSQL\17\data\postgresql.conf"
(Get-Content $pgConf) -replace "#listen_addresses = 'localhost'", "listen_addresses = '*'" | Set-Content $pgConf
```

**Step 2 — `pg_hba.conf` 允許 LAN 連線（固定來源 IP）**

```powershell
$pgHba = "C:\Program Files\PostgreSQL\17\data\pg_hba.conf"
Add-Content $pgHba "host    aisdlc    all    192.168.1.25/32    md5"
```

**Step 3 — 重啟服務 + 開放防火牆**

```powershell
$svcName = (Get-Service | Where-Object {$_.Name -like "postgresql*"} | Select-Object -First 1).Name
Restart-Service -Name $svcName
netsh advfirewall firewall add rule name="PostgreSQL 5432" dir=in action=allow protocol=TCP localport=5432
```

**Step 4 — 安裝 pgvector extension（Docker 推薦）**

```powershell
docker run -d --name pgvector-db -p 5432:5432 `
    -e POSTGRES_USER=koala -e POSTGRES_PASSWORD=koala5 -e POSTGRES_DB=aisdlc `
    pgvector/pgvector:pg17
```

**Step 5 — 建立 DB / 用戶 / extension**

```sql
CREATE DATABASE aisdlc;
CREATE USER koala WITH PASSWORD 'koala5';
GRANT ALL ON DATABASE aisdlc TO koala;
\c aisdlc
CREATE EXTENSION IF NOT EXISTS vector;
```

### 15.4 灰度驗證（both 模式）

```yaml
# config.local.yaml（gitignored）
storage:
  mode: "both"
  db_dsn: "postgresql+asyncpg://koala:koala5@192.168.1.133/aisdlc"
  dual_write_strict: true
  dual_read_resolution: "fail_loud"
```

本地網路無 TLS 時暫時跳過：

```bash
export AUTOCLAUDE_ALLOW_INSECURE_DB=1        # bash / macOS
$env:AUTOCLAUDE_ALLOW_INSECURE_DB = "1"      # PowerShell
```

### 15.5 執行 alembic migrations

```bash
export AUTOCLAUDE_MIGRATE_DSN="postgresql://koala:koala5@192.168.1.133/aisdlc"
export AUTOCLAUDE_ALLOW_INSECURE_DB=1
alembic upgrade head
alembic current   # 應顯示 0016_agt_phase1_memory（Improving_012 Phase 1：kb_metrics / user_preferences / goal_progress 三新表）
```

### 15.6 pgvector 語意查詢（選配）

```python
from autoclaude.infra.repositories.pg_memory_store import PgMemoryStore

store = PgMemoryStore(engine)
result = store.query("ModuleNotFoundError: No module named 'foo'")   # 精確文字匹配
# results = store.query_semantic(embedding, top_k=5, threshold=0.8)  # 語意向量匹配（HNSW m=16, ef=64）
```

---

## 16. 品質與工程治理

### 16.1 LOC 分級政策（ADR-SD07-001 + ADR-SD08-001）

| Tier | Budget | 說明 |
|------|--------|------|
| data | ≤ 150 | 資料模型 |
| plugin_entry | ≤ 250 | Plugin 進入點 |
| strategy | ≤ 300 | 策略模組 |
| adapter / contract | ≤ 400 | infra adapter / 契約 |
| service | ≤ 500 | service tier |
| absolute_limit | ≤ 750 | 全域絕對紅線（任何層級不得超）|
| special: CLAUDE.md | ≤ 400 | 文件治理 |

工具：`tools/check_loc_budget.py`（baseline 永久鎖定）；Hook `loc_budget_check.py`（PostToolUse warn / CLAUDE.md > 400 行 exit 2 阻斷）。當前 LOC violations = **0**。

### 16.2 importlinter（8 kept / 0 broken）

1. Plugins 不得 import 其他 plugins（改用 EventBus）
2. `autoclaude.core`（除 wiring）不得依賴 execution / infra
3. `_runner_internals` 不得被 core 或 plugins import
4. Brain 模組不得 import Executor 模組（改用 EventBus）
5. Executor 模組不得 import Brain 模組（改用 EventBus）
6. playbook_runner / strategy 模組不得 import checkpoint internal（改用 CheckpointPlugin public API）
7. Plugins 不得直接 import `utils.observability` helpers（改用 IObservabilityPort）
8. Plugins 不得直接 import `IKbMetricStore`（改用 FailureKnowledgeBase routing，Improving_012 Phase 1）

### 16.3 mutation / perf nightly（本地採集）

- **mutation**：`tools/run_local_nightly.ps1` 跑真 Docker；R61 kill_rate 76.51%（Killed 114 / Survived 35）；歷史必含 `source_sha256`，tail7 unique sha ≥ 7 防同 commit 重跑騙鎖（紀律 #12 / ADR-SD08-002 / ADR-SD09-002）。
- **perf**：baseline lock 須 `samples ≥ 20`；< 20 印 warning「statistical noise high; not blocking」；rc 三態 0/2/1 = 綠/warn/block（ADR-SD08-003 §2.6 v1.1）。

### 16.4 Nightly / CI 取證紀律（17 條，防再犯）

SD_09 W0~W3 共 40+ 輪 audit 累積，違反任一條 → P0 audit。完整版見 [Nightly_Forensic_Discipline.md](../06_quality/Nightly_Forensic_Discipline.md) v1.2。摘要：

1. stage rc 區分「真實失敗」vs「工具標準回報」（mutmut：`rc & 1 != 0`）
2. log 必須含完整統計（直查 raw store，不信任預設 dump）
3. PASS 聲稱須引 RunId log:L 行號（`logs/nightly_latest.log` 為單一真相）
4. 驗證鏡子自身要被驗證（`validate_*` 工具必有單元測試含假 PASS 場景）
5. 跨工具數字對齊 assertion
6. 採集寬鬆 vs 升級嚴格分軌（雙 env）
7. cache 路徑強制 fresh（`.mutmut-cache` / `.pytest_cache` / `.ac4_junit.xml` 跑前清）
8. 載具 `.sh` 必須 LF 行尾（`.gitattributes *.sh text eol=lf` + hook `check_sh_eol.py`）
9. Docker SKIP 跨 stage 一致（禁空殼 if 偽綠燈）
10. fallback 真實 jsonl 可區分（寫 `emit_real:bool` 布林標記）
11. latest log pointer 完整 run（末段 `Copy-Item` 完整 `$Log`）
12. mutation history 必含 `source_sha256`（tail 7 unique sha ≥ 7）
13. 觀察期 jsonl 進度可見（末段印 `END observation progress: ... (delta=N; stage=R)`）
14. schtasks vs 互動 PATH 等價 + StrictMode `$null.Property` 保護
15. 呼叫端工具路徑分隔符相容性（一律用正斜線 `tools/run_local_nightly.ps1`）
16. pytest 數字 SSOT 須註記隨機性與 fixture 前提（pytest-randomly 未啟用）
17. **zero-trust 須雙向**：subagent audit 結論本身亦須複核（嚴禁單憑 `fd`，未安裝時靜默回空 → 誤判不存在；以 `find`/`rg -l`/`ls` 獨立複核）

### 16.5 本機 CI 對等（push 前全綠）

- **Claude Code hooks**（5 個）：`check_lang.py`（語言）/ `enforce_docs_path.py`（文件路徑）/ `loc_budget_check.py`（LOC）/ `claude_md_freshness.py`（snapshot 新鮮度）/ `check_sh_eol.py`（.sh LF）。設定於 [.claude/settings.json](../../.claude/settings.json)。
- **git hooks**：`tools/git-hooks/` pre-commit / pre-push（`tools/install_git_hooks.ps1` 安裝）。
- **act**：`tools/run_act.ps1` 在 Linux 容器跑根層 autoclaude-ci.yml（於 monorepo 根執行）；`docker-compose.ci.yml`（pg17 對齊 CI）；`mock_brain_server.py`（本地 LLM mock）。
- **一鍵**：`tools/local_ci_gate.ps1`。詳見 [Local_CI_Parity_Guide.md](../08_deployment/Local_CI_Parity_Guide.md)。

---

## 17. 疑難排解

| 症狀 | 原因 | 解決方式 |
|------|------|---------|
| `Minimax API key 未設定` | `.env` / config 未填 | 確認 `MINIMAX_API_KEY` 或 `config.minimax.api_key` |
| `{path} 不是合法的 Playbook（缺少 tasks:）` | YAML 根節點非 dict 或缺 `tasks:` | 0.2+ 僅支援多步驟 Playbook，參考 `scripts/example_playbook.yaml` |
| `wexpect 未安裝`（Windows）| PTY 套件缺失 | `pip install wexpect`；缺失時 fallback subprocess（多數可用）|
| 中文輸出亂碼 | 編碼問題 | `config.claude.encoding: utf-8`；PowerShell 可 `chcp 65001` |
| evaluator_command 永遠失敗 | `shell=True`，路徑含空格 | 路徑以引號包覆；**勿從不可信來源載入 Playbook** |
| `halt_threshold_pct 必須 > compact_threshold_pct` | 門檻設定矛盾 | 調整 token_guard 門檻（pydantic validator 阻擋）|
| `storage.mode='both' 需要 db_dsn` | PG 模式缺 DSN | 提供 `db_dsn` 或 `AUTOCLAUDE_DB_DSN` |
| `port 5432 connection refused` | listen_addresses / 防火牆 | 見 §15.3 Step 1~3 |
| `ssl required but not provided` | DSN 缺 sslmode 且未設旗標 | `AUTOCLAUDE_ALLOW_INSECURE_DB=1`（僅限可信 LAN）|
| `connect() got unexpected keyword 'sslmode'` | asyncpg 不接受 psycopg2 風格 | factory.py 已自動轉換；確認最新版 |
| pgvector extension not found | DB 端未裝 extension | 見 §15.3 Step 4~5 |
| Bash 工具呼叫 ps1 報 exit 127 | 反斜線被 escape 吞噬 | 一律用正斜線 `tools/run_local_nightly.ps1`（紀律 #15）|

---

## 18. 進階用法

### 18.1 dry_run 測試模式

```python
runner = PlaybookRunner(cfg, minimax, hotkey, dry_run=True)
```

不實際呼叫 Claude Code，只以 regex keyword 合成輸出，供單元測試與 Playbook 結構驗證。

### 18.2 Mock CLI 整合測試

```bash
python tests/fixtures/dummy_cli.py    # 搭配 tests/fixtures/mock_playbook.yaml 做本地端到端測試
```

### 18.3 測試指令

```bash
python -m pytest tests/ -q                      # 全部（基線 2,931 passed / 122 skipped）
python -m pytest tests/test_playbook_runner.py -v
python -m pytest tests/test_decision.py -v      # MinimaxClient + StepMutation
python -m pytest tests/test_gap009.py -v        # Gap-009 ~ Gap-011 整合驗證
python -m pytest tests/plugins/ tests/core/ tests/infra/ -q
```

### 18.4 自訂 context 偵測 regex

`config.yaml` 中 `token_guard.context_patterns` 可追加自己的 pattern（須為合法 regex，以 `re.IGNORECASE` 編譯）。

---

## 19. 變更紀錄

### v1.1.0（2026-06-13，Improving_012 Phase 1 記憶基座）

- 新增 §11.4 記憶基座：F-C3 KB metrics 跨 session 持久化 / F-C1 使用者偏好 / F-C2 GoalProgressLedger。
- Ports 9 → 12（新增 `kb_metric_store` / `preference_store` / `spec_source`）；Plugins 13 → 16 active / 17 靜態（新增 `sdd_governance` / `preference_memory` / `goal_progress`）。
- importlinter 7 → 8 條 contract（Rule 8：Plugin 不得直接 import `IKbMetricStore`）。
- alembic 最新 revision：`0016_agt_phase1_memory`（kb_metrics / user_preferences / goal_progress 三新表）。
- 測試基線更新：2,931 passed / 122 skipped（2026-06-13 實測）。

### v1.0.0（2026-06-12，本手冊重寫）

- 全面對齊 SD_09 W3（R61）現況：微核心化架構（9 Ports + 13 Plugin + EventBus）、KernelResult SSOT、AutoResumeService 入口路徑。
- 新增 §2 微核心架構、§11 動態突變與自演化、§12 可觀測性、§16 品質與工程治理（LOC / importlinter 7 / mutation / perf / 17 條 nightly 取證紀律 / 本機 CI 對等）。
- 設定檔欄位全面對齊 `autoclaude/utils/config.py`（含 playbook 進階欄位、env 覆寫優先序、pydantic 防呆）。
- DAL 三後端 + DSN 優先序（`AUTOCLAUDE_DB_DSN` > `AUTOCLAUDE_PG_DSN` > config）。
- 測試基線更新：2,732 passed / 122 skipped。

### v0.3.0（2026-05-14，舊 docs/AutoClaude_Guide.md）

- Phase 6：PostgreSQL 後端正式上線（yaml_only / both / db_only 三段開關）+ pgvector HNSW。
- factory.py 修復 asyncpg sslmode 相容性。測試基線：1,034 passed / 10 skipped。

### v0.2.0（2026-04-30）

- 下線 LoopController 單任務模式；抽出 `perception/text_utils.py`；config 移除絕對路徑改 `config.local.yaml`。

### v0.1.0

- 初版 PlaybookRunner 狀態機 + Token Guard 雙門檻 + Checkpoint 斷點續傳 + AISDLC / AISDLC_SDD 工作流程偵測。

---

> **文檔元數據**：v1.1.0 ｜ 最後更新 2026-06-13 ｜ 對應 AutoClaude_Improving_012 Phase 1（記憶基座）｜ 適用 AutoClaude（套件 0.1.0，微核心架構）
> **SSOT 提醒**：架構細節（Plugin / Port / LOC tiers / importlinter rules）以 [CLAUDE.md](../../CLAUDE.md) 的 `[Architecture Snapshot]`（`tools/snapshot_sync.py` 自動生成）為單一真相；本手冊如與其牴觸，以 Snapshot 為準。
