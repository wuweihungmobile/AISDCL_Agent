# AutoClaude

> Claude Code 多步驟 Playbook 自動執行引擎，以狀態機管理執行流程、重試、Token 限制與錯誤升級。
> **Level 5 自治系統**：具備動態突變、自演化、目標對齊、跨 Session 持久化、元學習等高階閉環能力。
> **微核心化架構**：Hexagonal Architecture（9 Ports）+ Kernel/EventBus + 13 Plugin + DAL 三後端（File / InMemory / PostgreSQL）。

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]()
[![Tests](https://img.shields.io/badge/tests-2732%20passed%20%2F%20122%20skipped-brightgreen)]()
[![Status](https://img.shields.io/badge/status-active-green)]()
[![Autonomy](https://img.shields.io/badge/autonomy-Level%205%20(Evo--006)-orange)]()
[![Sprint](https://img.shields.io/badge/sprint-SD__09%20W3%20(R61)-blue)]()
[![Arch](https://img.shields.io/badge/import--linter-7%20kept%20%2F%200%20broken-blueviolet)]()

---

## ✨ 核心特色

### 🔄 多步驟閉環執行
- **多步驟 Playbook 狀態機**：以 YAML 定義一連串開發任務，Kernel 依序送 prompt 給 Claude Code 並驗證輸出。
- **完美 I/O 攔截**：透過 PTY（`wexpect`）/ subprocess 雙模式包裝 Claude Code，自動回應 `Y/n` 授權提示，過濾 ANSI 控制碼。
- **雙重驗證**：`expected_output_regex` + `evaluator_command` 雙保險，AI 說完成不算，由 Evaluator 親自跑。
- **Dry-run 模式**：`PlaybookRunner(dry_run=True)` 跳過 Claude Code 執行，以 regex keyword 合成輸出，供單元測試使用。

### 🧠 Minimax 修正大腦
- **Hallucination Guard**：Minimax 生成的 correction_prompt 自動驗證長度、與上次相似度、具體錯誤引用，過濾幻覺。
- **目標對齊（Gap-011-A）**：Playbook 可設定 `global_goal` 總目標，每次 Minimax 修正決策均以此為基準，避免修正方向偏離整體目標。
- **動態步驟突變（Gap-011-B / Evo-005）**：Minimax 可提議 7 種突變類型：
  - `REVISE_CURRENT`、`INJECT_AFTER`、`INJECT_BEFORE`、`GOTO_STEP`、`DELETE_STEP`、`SKIP_TO`、`CONDITIONAL`
  - 支援 `batch_mutations`（最多 3 個原子序列）
- **/compact MEMORY ANCHOR（Evo-006 Gap-039）**：壓縮後 anchor 持久注入 `[GLOBAL_GOAL]` + `[ACTIVE_TASK]` + `[SUCCESS_CONDITION]`，杜絕壓縮失憶導致的目標漂移。

### 🌱 Level 5 自演化引擎
- **MinimaxEvolver（AI 驅動）**：ESCALATION 時諮詢 Minimax 提議語意正確的演化策略（INJECT_STEP / SPLIT_STEP / REVISE_EVALUATOR）。
- **PlaybookEvolver（規則兜底）**：AI 失敗時退回規則引擎，基於失敗模式自動診斷並注入前置步驟或拆分複雜步驟。
- **跨步驟模式分析（Gap-033）**：多個步驟同類型錯誤（如 import / environment），自動注入全域環境初始化步驟。
- **演化效率最佳化（Evo-006 Gap-041）**：演化後從最後成功步驟恢復（透過 `completed_step_ids` checkpoint），不再強制 fresh=True 全重跑。
- **per-step 演化次數追蹤（Evo-006 Gap-048）**：同一步驟最多演化 2 次，防止單步消耗所有演化配額。

### 🛡️ 防護與保護
- **ErrorBudget**：per-error-class 重試上限（syntax:2, assertion:5, environment:0），防止無效重試耗盡預算。
- **元學習優先排序**：`FailureKnowledgeBase` 跨 session 記錄成功策略，`next_strategy()` 依歷史成功率優先排序。
- **KB 預播種（Evo-006 Gap-045）**：演化後新注入步驟自動預播種 KB（含 step_id 兜底查詢），首次 attempt 即可使用 PINPOINT 策略。
- **Token Guard**：偵測 context 使用率，達 80% 自動 `/compact`，達 90% 儲存 checkpoint 並排程恢復（已下沉 5 子模組：thresholds / compactor / git_verifier / watcher / policy）。
- **CONDITIONAL 安全防護（Evo-006 Gap-046）**：`condition_evaluator` 白名單 regex 驗證，拒絕 `&&` / `||` / `>` / `<` / 反引號 / `$(...)` 等鏈式攻擊向量。
- **跨步驟污染偵測**：`CrossStepValidator` 在步驟切換前以 `git status` 偵測未提交的異常修改（>5 個檔案時警告）。

### 💾 持久化與斷點續傳
- **斷點續傳**：原子寫入 checkpoint，崩潰或中斷後可從上次步驟繼續（`--fresh` 可忽略 checkpoint 重跑）。
- **三後端儲存策略**：`yaml_only`（預設）/ `both`（灰度雙寫）/ `db_only`（PostgreSQL 生產）— 零停機切換。
- **計數器跨 Session 持久化（Evo-006 Gap-042）**：`goto_counter`、`inject_before_counter`、`skip_to_counter`、`completed_step_ids`、`step_evolution_counter` 全部寫入 PlaybookCheckpoint，TOKEN_HALT / ESC+F12 / 演化重啟後正確恢復。

### 📡 可觀測性（SD_08 W4 / ADR-SD08-004）
- **IObservabilityPort**：可觀測性走 Port 注入而非散裝 import；`LocalLogger` adapter 為預設實作，預留 SD_10 OpenTelemetry 遷移面。
- **trace_id ContextVar**：跨 plugin / 跨 subprocess 自動傳遞 trace_id（`propagate_to_subprocess_env`），確保執行鏈路可追蹤。
- **KnowledgeBase metrics**：4 項指標（query / hit / pinpoint / fallback）內嵌於 `FailureKnowledgeBase`，aggregator pattern 統一收口。

### 🏗️ 微核心化架構（Phase 0~6 → SD_03 ~ SD_09 滾動演進）
- **Hexagonal Architecture**：`core/ports/`（9 Ports）定義抽象介面，`infra/adapters/` 實作，`plugins/`（13 active / 14 靜態）橫切關注點，各層禁止跨層 import（`.importlinter` 7 條 contract 強制）。
- **Kernel + EventBus + Plugin 體系**：Plugin 透過 EventBus 鬆耦合，PlaybookRunner 作為 Kernel facade（thin facade，無業務邏輯）。
- **DAL 三後端**：FileStateRepository / InMemoryStateRepository / PgStateRepository + DualStateRepository（File 主 + PG 影）。
- **LOC 分級政策（ADR-SD07-001）**：data ≤150 / plugin_entry ≤250 / strategy ≤300 / adapter ≤400 / contract ≤400 / service ≤500 / 絕對紅線 ≤750；CI hook 強制，當前 violations = 0。
- **god-object 徹底拔除**：`_runner_impl.py`（2,236 行）+ `_runner_internals.py` 已物理刪除（SD_06 W6 G6），importlinter Rule 3 設「防復活柵欄」。

---

## 🚀 快速開始

### 1. 安裝

```bash
git clone https://github.com/wuweihungmobile/AutoClaude.git
cd AutoClaude
pip install -e .[dev,notifications]

# 架構約束檢查（import-linter）
pip install -e .[lint]

# PostgreSQL 後端（選配，Phase 6）
pip install -e .[postgres]            # SQLAlchemy + asyncpg + psycopg2 + alembic + tenacity + cachetools
pip install -e .[postgres,pgvector]   # 加 pgvector 向量查詢
```

> ⚠️ `alembic` 走同步連線，migration 工具需 `psycopg2-binary`（已含於 `[postgres]` extra）；缺少時 `alembic upgrade head` 會報 `ModuleNotFoundError`。

### 2. 設定

```bash
cp .env.example .env
# 編輯 .env，填入 MINIMAX_API_KEY

cp config.local.yaml.example config.local.yaml
# 編輯 config.local.yaml，填入個人化設定（gitignored）
```

**Storage 模式設定（config.yaml）**：

```yaml
storage:
  mode: "yaml_only"   # yaml_only（預設）| both（灰度）| db_only（生產）
  # db_dsn: "postgresql+asyncpg://user:pass@host/db?sslmode=require"
  # 或設定環境變數 AUTOCLAUDE_DB_DSN
```

### 3. 撰寫 Playbook

```yaml
# scripts/my_playbook.yaml
version: "1.0"
project: "MyProject"

global_goal: |
  建立一個通過所有單元測試的 FastAPI 驗證模組。

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
    evaluator_command: "pytest tests/test_foo.py -v"
    evaluator_timeout_seconds: 60
    maintain_context: true
```

完整範例請參考 [scripts/example_playbook.yaml](scripts/example_playbook.yaml)。

### 4. 執行

```bash
# 使用個人化設定
python -m autoclaude scripts/my_playbook.yaml --config config.local.yaml

# 從頭重跑（忽略 checkpoint）
python -m autoclaude scripts/my_playbook.yaml --fresh

# 安裝後可使用 entrypoint
autoclaude scripts/my_playbook.yaml
```

---

## 🏗️ 架構

### 目錄結構

```
autoclaude/
├── __main__.py / main.py        # CLI 入口（argparse、Playbook 驗證）
├── core/                        # 微核心層
│   ├── kernel.py                # Kernel：協調 Plugin 生命週期 + EventBus dispatch
│   ├── kernel_state.py          # KernelState：純資料類別
│   ├── event_bus.py             # EventBus：plugin 間解耦事件廣播（lazy 注入 trace_id）
│   ├── hookspec.py              # HookSpec：Plugin 介面合約
│   ├── wiring.py                # build_kernel：Plugin 註冊（_REGISTER_ORDER SSOT）與相依注入
│   ├── orchestration/           # OrchestrationCoordinator（SD_06 W1）
│   ├── ports/                   # 9 個抽象介面（Hexagonal Architecture）
│   │   ├── brain.py             # BrainPort（Minimax / LLM）
│   │   ├── executor.py          # ExecutorPort（Claude Code / 子程序）
│   │   ├── evaluator.py         # EvaluatorPort
│   │   ├── memory_store.py      # MemoryStorePort（FailureKnowledgeBase 後端）
│   │   ├── embedder.py          # EmbedderPort（向量嵌入）
│   │   ├── vector_search.py     # VectorSearchPort（pgvector 語意查詢）
│   │   ├── observability.py     # IObservabilityPort（SD_08 W4 / ADR-SD08-004）
│   │   ├── playbook_repository.py
│   │   └── state_repository.py  # StateRepositoryPort（Checkpoint 持久化）
│   └── services/
│       ├── mutation/            # StepMutation 套用邏輯
│       └── auto_resume.py       # 跨 run 自動恢復
├── infra/                       # 基礎設施層（adapters + repositories）
│   ├── adapters/
│   │   ├── minimax_brain.py     # BrainPort 實作
│   │   ├── pty_executor.py      # ExecutorPort（PTY / subprocess 雙模式）
│   │   ├── dry_run_executor.py  # 測試用 ExecutorPort
│   │   ├── shell_evaluator.py   # EvaluatorPort 實作
│   │   └── observability/       # LocalLogger（IObservabilityPort 實作，SD_08 W4）
│   └── repositories/            # DAL 三後端
│       ├── factory.py           # build_state_repository（yaml_only/both/db_only）
│       ├── _pg_models.py        # SQLAlchemy ORM models（含 pgvector embedding）
│       ├── file_state_repository.py        # YAML / JSON
│       ├── pg_state_repository.py          # PostgreSQL + asyncpg
│       ├── dual_state_repository.py        # File 主 + PG 影；fail_loud/yaml_wins/db_wins
│       ├── in_memory_state_repository.py   # 測試用
│       ├── file_memory_store.py / pg_memory_store.py  # FailureKnowledgeBase 後端
│       └── file_playbook_repository.py / pg_playbook_repository.py
├── plugins/                     # 13 個 active / 14 個靜態 Plugin（橫切關注點）
│   ├── pre_run_validator_plugin.py / hotkey_plugin.py（條件式註冊）
│   ├── cross_step_validator_plugin.py / token_guard_plugin.py
│   ├── global_goal_anchor_plugin.py / playbook_persistence_plugin.py
│   ├── fast_path_plugin.py / notification_plugin.py / knowledge_base_plugin.py
│   ├── goal_synthesis_plugin.py / convergence_plugin.py / evolution_plugin.py
│   └── goto_counter_plugin.py / checkpoint_plugin.py（已拆 package）
├── models/
│   └── playbook.py / decision.py / escalation.py / step_mutation.py
├── perception/
│   └── pty_wrapper.py / stream_reader.py / text_utils.py / hotkey_handler.py
├── decision/
│   └── minimax_client.py / prompt_builder.py
├── execution/                   # playbook_runner（thin facade）+ 子模組
│   ├── playbook_runner.py       # Kernel facade（_runner_impl/_runner_internals 已刪除）
│   ├── steps_orchestrator/      # 步驟編排
│   ├── workflow_detector.py / failure_tracker.py / convergence_monitor.py
│   ├── error_classifier.py / error_budget.py / cross_step_validator.py
│   ├── boot_helper.py / compact_controller.py / escalation_dumper.py
│   └── halt_handler.py / prompt_dispatcher.py / pre_run_validator.py / evaluator.py
├── evolution/
│   └── minimax_evolver.py / playbook_evolver.py
└── utils/
    ├── config.py                # AppConfig + StorageConfig（Pydantic Settings）
    ├── checkpoint_manager.py / token_tracker.py / knowledge_base.py
    └── trace_context.py / knowledge_base_metrics.py（SD_08 W4 可觀測性）

alembic/versions/               # DB migrations（0001 → 0015，共 15 個）
├── 0001_initial.py … 0004_pgvector.py（pgvector + HNSW m=16, ef_construction=64）
├── 0009_three_tier_schema.py … 0011_rbac_tables.py
└── 0013_drift_log.py / 0014_config_audit_log.py / 0015_merge_sd06_optional_gin.py

tests/                          # 2,732 passed / 122 skipped（SD_09 W3 R61 基線）
├── core/ plugins/ infra/       # Kernel / 13 Plugin / adapters + repositories
├── contract/                   # DAL 契約測試（File vs PG 行為等價）+ runner 防護
├── equivalence/ cli/ integration/ perf/   # 等價 / CLI / 整合 / 性能 baseline
└── tools/                      # hooks / nightly 驗證鏡子自身測試（404 passed）
```

### Plugin 註冊順序（`wiring._REGISTER_ORDER` — SSOT）

`pre_run_validator` → `hotkey`（條件式）→ `cross_step_validator` → `token_guard` → `global_goal_anchor` → `playbook_persistence` → `fast_path` → `notification` → `knowledge_base` → `goal_synthesis` → `convergence` → `evolution` → `goto_counter` → `checkpoint`

> EventBus 排序主鍵為 `plugin.priority()`，tie-breaker 為註冊順序；`fast_path` / `notification` / `knowledge_base` / `goal_synthesis` 共用 priority=50，順序即 tie-breaker，重排會破壞 PRE_ATTEMPT 早觸發語意。

### 架構約束（import-linter 7 kept / 0 broken）

| # | Contract | 規則 |
|---|----------|------|
| 1 | plugin-isolation | Plugin 之間不可互相 import（協作走 EventBus） |
| 2 | core-purity | `core`（除 wiring）不可依賴 `execution` / `infra` |
| 3 | runner-internals-isolation | `_runner_internals` 不可被 core / plugins import（防復活柵欄） |
| 4 | brain-executor-isolation | Brain 模組不可 import Executor 模組（走 EventBus） |
| 5 | executor-brain-isolation | Executor 模組不可 import Brain 模組（走 EventBus） |
| 6 | runner-no-checkpoint-logic | `playbook_runner` / strategy 不可 import checkpoint 內部模組（走 CheckpointPlugin 公開 API） |
| 7 | plugin-no-utils-observability | Plugin 不可直接 import `utils.observability` helpers（走 IObservabilityPort） |

### DAL 三後端策略

| 模式 | 行為 | 適用情境 |
|------|------|----------|
| `yaml_only`（預設） | 純 File backend，零 PG 依賴 | 開發 / 單機 / v1.x 相容 |
| `both` | File 主寫 + PG 影子；File 主讀，PG 災難回復 | PG 上線首兩週灰度驗證（≥24h + metrics 全零） |
| `db_only` | 純 PG backend | Production 穩定後（PM + Stakeholder 簽核） |

**DSN 解析優先級**：環境變數 `AUTOCLAUDE_DB_DSN` > `AUTOCLAUDE_PG_DSN`（deprecated） > `config.storage.db_dsn`

**安全**：DSN 必須含 `?sslmode=require`（TLS 強制）；僅開發可設 `AUTOCLAUDE_ALLOW_INSECURE_DB=1` 跳過。

### 狀態機流程

```
INIT → PRE_RUN_VALIDATE → CONTEXT_NEGOTIATION → EXECUTE(step N)
                                                      ↓
                                             (Token Guard 監控)
                                           >= 80%  → TOKEN_COMPACT（注入 [GLOBAL_GOAL] anchor）
                                           >= 90%  → TOKEN_HALT（儲存含計數器 checkpoint）
                                                      ↓
                                                  EVALUATE
                                              ┌───────┴───────┐
                                           成功               失敗
                                              ↓               ↓
                                       CrossStepValidate  CORRECTION (Minimax)
                                              ↓               └─ retry / ESCALATION
                                         next step                 ↓
                                                          MinimaxEvolver (AI)
                                                              ↓ (失敗 fallback)
                                                          PlaybookEvolver (規則)
                                                                ↓
                                              ↓
                                           DONE → GOAL_SYNTHESIS（全局目標驗證）
                                                  ├─ 通過 → 清除 checkpoint，桌面通知
                                                  └─ 失敗 → MinimaxEvolver 補完（Gap-044）
```

---

## 📋 Playbook 欄位說明

### Playbook（頂層）

| 欄位 | 類型 | 預設 | 說明 |
|------|------|------|------|
| `version` | `str` | `"1.0"` | Playbook 版本 |
| `project` | `str` | — | 專案名稱 |
| `global_goal` | `str?` | `None` | **系統總目標**（Gap-011-A）：Minimax 決策對齊 + compact anchor 持久化 |
| `workflow_type` | `str` | `"auto"` | `auto` / `aisdlc` / `aisdlc_sdd` |
| `global_invariants` | object | — | `max_retries_per_step`、`auto_compact_interval` |
| `context_negotiation` | object? | `None` | Context 協商設定 |
| `tasks` | list | — | 步驟清單（`PlaybookTask[]`） |

### PlaybookTask（步驟）

| 欄位 | 類型 | 預設 | 說明 |
|------|------|------|------|
| `step_id` | `str` | — | 步驟 ID（例如 T01） |
| `name` | `str` | — | 步驟名稱 |
| `prompt` | `str` | — | 送給 Claude Code 的 prompt |
| `command` | `str?` | `None` | 直接執行的 shell 指令（可選） |
| `expected_output_regex` | `str?` | `None` | 評估成功的 regex（自動 strip ANSI） |
| `evaluator_command` | `str?` | `None` | 額外 shell 評估指令（雙重驗證） |
| `evaluator_timeout_seconds` | `int` | `120` | Evaluator 超時秒數 |
| `max_retries` | `int?` | global | 步驟最大重試次數 |
| `maintain_context` | `bool` | `True` | 是否傳遞 `--continue` 給 Claude Code |
| `token_guard` | object? | `None` | per-step token guard override（SD_05 W2） |

### PlaybookCheckpoint（跨 Session 持久化欄位）

| 欄位 | 類型 | 說明 |
|------|------|------|
| `step_idx` / `step_id` | — | 恢復定位 |
| `completed_step_ids` | `list[str]` | **Gap-041**：演化後跳過已完成步驟 |
| `goto_counter` | `dict[str, int]` | **Gap-042**：GOTO_STEP 計數器跨 Session |
| `inject_before_counter` | `dict[str, int]` | **Gap-042**：INJECT_BEFORE 計數器 |
| `skip_to_counter` | `dict[str, int]` | **Gap-042**：SKIP_TO 計數器 |
| `step_evolution_counter` | `dict[str, int]` | **Gap-048**：per-step 演化次數（上限 2） |
| `run_id` / `goal_task_id` | `str` | **SD_06 W5**：三層任務模型關聯 |

---

## 🧪 測試

```bash
# 全部測試（2,732 passed / 122 skipped，SD_09 W3 R61 基線）
python -m pytest tests/ -q

# 特定模組
python -m pytest tests/test_playbook_runner.py -v
python -m pytest tests/test_decision.py -v
python -m pytest tests/core/ tests/plugins/ -v     # Kernel + 13 Plugin
python -m pytest tests/infra/ tests/contract/ -v   # DAL 三後端 + 契約等價
python -m pytest tests/tools/ -v                   # hooks / nightly 驗證鏡子自身測試

# 架構約束檢查（import-linter）
PYTHONUTF8=1 lint-imports                          # 7 kept / 0 broken
```

> **隨機性註記**：`pytest-randomly` 未啟用，測試順序由 collection 確定（紀律 #16）。

---

## 🟢 本機 CI 對等 + Nightly 機制

### 本機 CI 對等（push 前全綠，免再被 GitHub CI 紅燈打臉）

善用本機 Docker，把 CI 把關前移到本機；**本機綠了才 push**。詳見
[docs/08_deployment/Local_CI_Parity_Guide.md](docs/08_deployment/Local_CI_Parity_Guide.md)。

```powershell
powershell -ExecutionPolicy Bypass -File tools/install_git_hooks.ps1     # 1) 裝 git hooks（commit/push 自動把關）
powershell -ExecutionPolicy Bypass -File tools/local_ci_gate.ps1         # 2) 一鍵本機 CI 閘門（鏡像 ci.yml push jobs）
powershell -ExecutionPolicy Bypass -File tools/run_act.ps1 -Job test     # 3) act：在 Linux 容器跑真 CI（攔 Win/Linux 差異）
docker compose -f docker-compose.ci.yml up -d                            # CI 對等 PG（pg17）
docker compose -f docker-compose.llm.yml --profile mock up -d            # 本地 LLM/Brain mock
```

### Nightly 採集（SD_08/SD_09 觀察期）

```powershell
# 6 stage 全綠：mutation / pg-e2e / perf / drift / obs（+ 真 Docker mutation）
powershell -ExecutionPolicy Bypass -File tools/run_local_nightly.ps1
```

- **Mutation testing（ADR-SD08-002）**：`mutmut==2.4.3`（鎖版；3.x CLI 重寫不相容），TokenGuardPlugin pilot；最新 kill_rate ≈ **76.5%**（真 Docker，分模組目標 75/70/65%）。
- **Perf baseline（ADR-SD08-003）**：p95 三級告警（0/2/1 = 綠/warn/block）；`samples ≥ 20` 才 lock，不足印 statistical-noise warning。
- **取證紀律**：17 條 Nightly/CI Forensic Discipline（stage rc 真實性、PASS 引 RunId 行號、驗證鏡子自身要被驗證、cache 強制 fresh、Docker SKIP 跨 stage 一致…）。完整版見 [docs/06_quality/Nightly_Forensic_Discipline.md](docs/06_quality/Nightly_Forensic_Discipline.md)。

### Claude Code Hooks（5 個啟用中）

| Hook | 事件 | 動作 |
|------|------|------|
| 語言檢查 | Stop | 偵測韓/日/簡體字 → warn |
| 文件路徑強制 | PreToolUse(Write) | `.md` 須在 `docs/0[1-8]_*/` 白名單，違規阻斷 |
| LOC 預算檢查 | PostToolUse(Edit\|Write) | 超 tier budget → warn；CLAUDE.md > 400 行 → 阻斷 |
| Snapshot 新鮮度 | Stop | snapshot drift → warn |
| .sh LF 行尾 | PostToolUse(Edit\|Write) | `.sh` 含 CRLF → 阻斷（紀律 #8） |

---

## 📈 演進歷程

### Level 5 閉環升級（Evo-001 ~ Evo-006）

| 版本 | 主題 | 核心成果 |
|------|------|---------|
| Evo-001 | 基礎閉環 | 狀態機、PTY 攔截、Minimax 修正 |
| Evo-002 | 元學習 | KnowledgeBase 跨 session、ErrorBudget |
| Evo-003 | 動態突變 | Gap-011-B 七種步驟突變、batch_mutations |
| Evo-004 | 目標對齊 | Gap-011-A `global_goal`、context bridge |
| Evo-005 | 自演化引擎 | MinimaxEvolver、跨步驟模式分析 |
| Evo-006 | 持久化與安全 | compact anchor、計數器跨 Session、KB 預播種、CONDITIONAL 安全防護 |

### 微核心化重構 + 工程治理（SD_Improving_03 ~ SD_09）

| Sprint | 主題 | 狀態 |
|--------|------|------|
| Phase 0~6 | baseline + `core/`（Kernel/EventBus/HookSpec/Ports）+ `infra/` + 12 Plugin 拆解 + DAL 抽象化 + pgvector HNSW | ✅ 完成 |
| SD_03 | PlaybookRunner → Kernel facade（G3 三方簽核） | ✅ 完成 |
| SD_04 | god-object 拆解 | ✅ 完成 |
| SD_05 | Counter SSOT + TokenGuard 下沉 5 子模組 + Mutation v2 | ✅ 完成 |
| SD_06 | PG 三層任務模型 + Brain/Executor EventBus 分工 + `_runner_internals` 物理刪除 | ✅ 完成 |
| SD_07 | LOC 分級政策（ADR-SD07-001）+ 肥胖檔案二度拆 + 6 議題 e2e；**2,012 passed** | ✅ 完成 |
| SD_08 | 文件治理（CLAUDE.md ≤ 400）+ 可觀測性 IObservabilityPort + mutation/perf baseline + 5 ADR；**≥ 2,100 passed** | ✅ 完成 |
| **SD_09** | **觀察期 #1/#2/#3 nightly 採集 + W3 zero-trust audit 連 38 輪閉環（R24~R61）；2,732 passed / 122 skipped** | 🟡 進行中 |

**最新基線（SD_09 W3 R61，2026-06-12）**：**2,732 passed / 122 skipped**（88.69s）；import-linter **7 kept / 0 broken**；LOC violations = **0**；ADR 共 **17 條**（SD06~SD09）；nightly 6 stage 全綠（kill_rate 76.51%、perf green）。四方 zero-trust audit OVERALL PASS（0 P0 / 0 P1 / 0 P2）。

> **觀察期進度**：#1 mutation kill_rate 達標（unique sha 源碼演進閘門待 W1）；#2 AC4 p95<60ms 達標日 ~2026-06-16；#3 drift_log 30 天零 severity 達標日 ~2026-06-24。

---

## 🗄️ PostgreSQL 後端（Phase 6 選配）

### 快速啟用（Both 模式灰度）

```bash
# 1. 安裝依賴
pip install -e .[postgres]

# 2. 設定環境變數
export AUTOCLAUDE_DB_DSN="postgresql+asyncpg://koala:koala5@192.168.1.133/aisdlc?sslmode=require"
# 本地 LAN 無 SSL 時暫用：export AUTOCLAUDE_ALLOW_INSECURE_DB=1

# 3. 執行 migrations（0001 → 0015）
export AUTOCLAUDE_MIGRATE_DSN="$AUTOCLAUDE_DB_DSN"
alembic upgrade head

# 4. 啟動灰度驗證（config.yaml）
# storage:
#   mode: "both"
#   dual_write_strict: true
#   dual_read_resolution: "fail_loud"
```

### DB 主機設定（Windows 11 — 192.168.1.133）

詳細步驟請參考 [docs/08_deployment/DB_Only_Switch_Runbook.md](docs/08_deployment/DB_Only_Switch_Runbook.md)。

摘要（PowerShell 系統管理員）：

```powershell
# 1. postgresql.conf：listen_addresses = '*'
# 2. pg_hba.conf：host aisdlc all 192.168.1.25/32 md5
# 3. 重啟服務 + 開防火牆 port 5432
# 4. 安裝 pgvector（⚠️ 官方 Releases 無 Windows 包）：
#    方式 A（推薦）：https://github.com/andreiramani/pgvector_pgsql_windows/releases（支援 PG 13~18）
#    方式 B：nmake /F Makefile.win 原始碼編譯（需 Visual Studio）
#    方式 C：Docker Desktop（需先停止原生 PG 服務）
# 5. CREATE EXTENSION IF NOT EXISTS vector;
```

### 切換至 db_only（生產）— 紅線提醒

前置條件：port 5432 連通 → `alembic upgrade head` → `both` 模式 ≥ 24h metrics 全零 → PM + Stakeholder 簽核

> ⛔ **Production 上線紅線**：真正上線前必須由人類 DBA 在公司 staging（≥ 1M 真實列）重跑 + 人類 PM 親簽 release approval。SD_08 W5 已落地 ADR-SD08-005 雙軌制 + `pg_health.py` WAL lag adapter，正式啟用延 SD_09+（雙條件：可觀測性 GA + 30 天零 drift）。

```yaml
storage:
  mode: "db_only"
```

---

## 📦 依賴套件

| 套件 | 用途 | extra |
|------|------|-------|
| `pydantic>=2.0` | 資料驗證 | core |
| `pyyaml>=6.0` | Playbook 解析 | core |
| `httpx>=0.27` | Minimax API HTTP | core |
| `wexpect>=4.0` | Windows PTY（缺失時 fallback subprocess） | core（Win） |
| `keyboard>=0.13` | ESC+F12 全域熱鍵 | core |
| `pytest` / `pytest-mock` / `ruff` / `hypothesis` / `cachetools` | 開發/測試工具 | `dev` |
| `mutmut==2.4.3` | Mutation testing（鎖版，僅 Linux container） | `mutation` |
| `import-linter>=2.0` | 架構約束檢查 | `lint` |
| `plyer` / `win10toast` | 桌面通知 | `notifications` |
| `sqlalchemy>=2.0` + `asyncpg>=0.29` + `psycopg2-binary>=2.9` | PostgreSQL 後端 | `postgres` |
| `alembic>=1.13` + `tenacity>=8.2` | DB migrations + 連線重試 | `postgres` |
| `pgvector>=0.3` | 向量查詢（需 pgvector extension） | `pgvector` |

```bash
pip install -e .[dev,notifications]           # 開發環境
pip install -e .[lint]                        # 架構約束檢查
pip install -e .[postgres]                    # 加 PostgreSQL 後端
pip install -e .[postgres,pgvector]           # 加向量查詢
```

> Python `>=3.11` required。

---

## 🛡️ 安全提醒

- **`.env` 含 API Key 絕不可 commit**（已加入 `.gitignore`）
- **PostgreSQL DSN 必須含 TLS**（`?sslmode=require`）；`AUTOCLAUDE_ALLOW_INSECURE_DB=1` 僅供 dev/test
- **pg_hba.conf 建議固定 IP**（`192.168.1.25/32`），避免整網段授權
- **`evaluator_command` / `command` 等同信任源**：使用 `shell=True` 執行，請勿從不可信來源載入 Playbook
- **`condition_evaluator` 內建白名單**（Gap-046）：自動拒絕含 `&&` / `||` / `>` / `<` / 反引號 / `$(...)` 的指令
- **`config.local.yaml` 含個人路徑**（已加入 `.gitignore`）

---

## 📚 文件

| 文件 | 說明 |
|------|------|
| [CLAUDE.md](CLAUDE.md) | 開發者貢獻指南、Agent 載入規則、模型欄位完整說明、Architecture Snapshot SSOT |
| [docs/05_development/sprint_history.md](docs/05_development/sprint_history.md) | Sprint 完整脈絡（SD_03 起，含 SD_09 W3 各 Round） |
| [docs/04_planning/ADR/](docs/04_planning/ADR/) | 架構決策記錄（SD06~SD09 共 17 條） |
| [docs/06_quality/Nightly_Forensic_Discipline.md](docs/06_quality/Nightly_Forensic_Discipline.md) | Nightly / CI 取證紀律 17 條 |
| [docs/08_deployment/Local_CI_Parity_Guide.md](docs/08_deployment/Local_CI_Parity_Guide.md) | 本機 CI 對等指南（git hooks + act + docker-compose） |
| [docs/08_deployment/DB_Only_Switch_Runbook.md](docs/08_deployment/DB_Only_Switch_Runbook.md) | PostgreSQL 生產切換 SOP（Windows 11 版） |
| [docs/05_development/gate_audit.md](docs/05_development/gate_audit.md) | G1~G6 Gate 簽核記錄 |
| [docs/05_development/risk_log.md](docs/05_development/risk_log.md) | 重構風險登記 |
| [scripts/example_playbook.yaml](scripts/example_playbook.yaml) | AISDLC_SDD TDD 開發循環 Playbook 範本 |

---

## 🤝 貢獻

請參考 [CLAUDE.md](CLAUDE.md) 中的「開發-編譯-測試循環」與專案規範（含 LOC 分級政策、import-linter 約束、文檔目錄規範、Nightly 取證紀律）。

---

## 📄 授權

詳見 LICENSE（待補）。
