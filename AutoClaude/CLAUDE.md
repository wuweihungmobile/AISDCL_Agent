# CLAUDE.md — Claude Code Project Guidance

**Last Updated**: 2026-07-19（權威以 git log 為準） | **AISDLC Version**: v0.09 | **Status**: **Improving_012 完成（三能力 A/B/C 全交付）**。Phase 3 F-A1 GoalDecomposer 收尾：`IBrain.decide_decomposition` + `supports_decomposition`（additive，capability 守門不靜默降級）+ `execution/goal_decomposer.py`（三道有界閘 ≤24 硬上限／Kahn 無環／非空 prompt，超限拒絕不重試、1 次 Brain 呼叫非遞迴）+ 🔴 signoff 硬閘 + `wiring.build_goal_decomposer` 注入 F-A2 ToolInvocationAdapter（消費 allowlist）。三方 zero-trust audit OVERALL PASS（P0=0/P1=0）。full pytest 🔴 基線數字唯一出處＝根層 ONBOARDING.md §7（出廠環境定義、選配與巢狀 session 變因、歷史校正記事均收斂該節，本檔不重複數字——R13 收斂＋`tools/check_pytest_baseline_sites.py` 機械鎖）、coverage 100%、importlinter 8 kept、LOC=0。詳見 [AutoClaude_Improving_012.md](docs/04_planning/AutoClaude_Improving_012.md) §5 Phase 3。

> **🔴 Important Notice 🔴** This file provides critical guidance for Claude Code (claude.ai/code). All instructions here OVERRIDE default behavior and must be followed exactly.

---

## 📍 快速導覽（ADR-SD08-001 v1.1）

- **規範 / 開發循環 / 模型 / CLI**：本檔（CLAUDE.md，≤ 400 行）
- **Sprint 完整脈絡（SD_03 起）**：[docs/05_development/sprint_history.md](docs/05_development/sprint_history.md)
- **架構決策（ADR）**：[docs/04_planning/ADR/](docs/04_planning/ADR/)（SD06~SD09；條數以目錄實數為準，本檔不重複計數）
- **新 Sprint W 期間紀錄 SOP**：W 期間 Round 直接寫 `sprint_history.md §1.N`；CLAUDE.md sprint H3 ≤ 15 行（[Sprint_Round_Recording_SOP](docs/05_development/Sprint_Round_Recording_SOP.md) + [ADR §9](docs/04_planning/ADR/ADR-SD08-001-claude-md-budget.md)）

---

## 🔴 溝通語言規範

**CRITICAL: 所有執行過程中的回覆必須使用繁體中文。絕對禁止韓文（한국어）、日文、簡體中文。** 過去曾發生長對話後回覆語言自動切換為韓文的問題，**每次回覆前必須自我檢查語言**。

| 對象 | 要求 |
|------|------|
| 回覆訊息 / 狀態更新 / Todo 任務描述 | 繁體中文（✅「完成」/ ❌「Perfect, completed」） |
| 專有名詞（AISDLC, API, Git, Docker 等） | 保持原文 |
| 自我檢查 | 每次回覆前確認語言、無韓/日/簡體混入 |

> **自動化**：`tools/hooks/check_lang.py` 於 Stop 事件偵測非繁中字元（warn-only；Hook 僅能 post-facto 提示，無法直接改變 LLM 內容生成）。

---

## 🔴 開發-編譯-測試循環強制規則（CRITICAL）

**原則**：每完成一支程式立即執行編譯-測試循環，**絕不累積開發**。

```
開發 1 支 → 立即編譯 → 編譯失敗：🔴 立即停止修復 → 編譯成功 →
執行單元測試 → 測試失敗：🔴 立即停止依規格修復 → 測試通過 → 繼續下一支
```

**絕對禁止**：(1) 累積開發多支才編譯；(2) 編譯失敗繼續開發；(3) 跳過單元測試；(4) 測試失敗後註解掉測試。

詳見：[Development_Build_Test_Cycle.md](AISDLC_v0.09/guides/user/process/Development_Build_Test_Cycle.md)。

> **自動化**：CLAUDE.md §開發-編譯-測試循環為 prompt 層規範，由 LLM 自律執行；Hook 層補強規劃中（`tools/hooks/build_test_cycle.py` 為 backlog；當前由人類紀律執行）。

---

## 📂 專案文檔目錄規範

**寫檔強制檢查**：(1) 確認文檔類型；(2) 確認 docs/ 編號子目錄；(3) 確認命名格式 PascalCase / Snake_Case；(4) 絕不寫入工作目錄外。

| 文檔類型 | 目錄位置 |
|---------|---------|
| PRD, FRD, User Stories | `docs/01_requirements/` |
| SRD, API Specification | `docs/02_architecture/` |
| Test Plan, AT, Test Reports | `docs/03_testing/` |
| Roadmap, Estimation, Task Breakdown | `docs/04_planning/` |
| Iteration Plans, Progress Logs | `docs/05_development/` |
| Code Quality, Security, Performance | `docs/06_quality/` |
| UI/UX, Database Design | `docs/07_design/` |
| CI/CD, Release Notes | `docs/08_deployment/` |

詳見：[DEVELOPMENT_DIRECTORY_STRUCTURE.md](AISDLC_v0.09/DEVELOPMENT_DIRECTORY_STRUCTURE.md)。

> **自動化**：`tools/hooks/enforce_docs_path.py` 於 PreToolUse Write 強制白名單目錄（`docs/0[1-8]_*/` + 根層 `CLAUDE.md`/`README.md`），違規即阻斷。

---

## 🤖 Agent 自動載入

| Agent | 角色 | 使用時機 | 配置檔 |
|-------|------|---------|--------|
| **dev-developer** | 開發 | 程式碼實作、編譯測試 | [06](AISDLC_v0.09/agent/core/06.dev-developer-zh.yaml) |
| **qa-tester** | 測試 | 測試設計、執行驗證 | [07](AISDLC_v0.09/agent/core/07.qa-tester-zh.yaml) |
| **sa-analyst** | 系統分析 | 需求分析、功能設計 | [04](AISDLC_v0.09/agent/core/04.sa-analyst-zh.yaml) |
| **sd-architect** | 架構設計 | 技術架構、系統設計 | [05](AISDLC_v0.09/agent/core/05.sd-architect-zh.yaml) |
| **pm-po-agent** | 專案管理 | 需求優先級、規劃 | [03](AISDLC_v0.09/agent/core/03.pm-po-agent-zh.yaml) |
| **ba-business-analyst** | 業務分析 | 業務邏輯驗證 | [02](AISDLC_v0.09/agent/core/02.ba-business-analyst-zh.yaml) |

**自動載入流程**：識別任務類型 → 讀對應 YAML → 載入 core_principles / quality_standards / collaboration_rules → 按 Agent 規範執行。使用 AISDLC workflow 前載入 [AISDLC_INIT.md](AISDLC_v0.09/AISDLC_INIT.md)；情境啟動 `AISDLC [情境代碼] [專案簡述]`，詳見 [SCENARIO_SELECTOR.md](AISDLC_v0.09/guides/user/onboarding/SCENARIO_SELECTOR.md)。
> ⚠️ 本檔所有 `AISDLC_v0.09/` 連結指向的目錄**未隨 monorepo 入庫**（僅存於原始獨立 AutoClaude repo；R13 DOC-2 查證全 repo 零命中）——在本 monorepo 內點按必失效；方法論資產請改用姊妹專案 [../AISDLC_SDD/](../AISDLC_SDD/)（LATEST 版）。

---

## 📋 專案開發規範

- **文檔命名**：PascalCase / Snake_Case + 英文 + 類型前綴（`PRD_`, `FRD_`, `Sprint_`）
- **ID 命名**：`F-XXX` Feature / `NFR-XXX` / `EPIC-XXX` / `US-XXX` / `AC-XXX-Y` / `API-XXX` / `TC-XXX-Y-Z` / `BUG-XXX` / `TECH-XXX`（詳見 [AISDLC_ID_Naming_Convention.md](AISDLC_v0.09/guides/system/naming/AISDLC_ID_Naming_Convention.md)）
- **品質檢查**：完整性、可讀性、技術文檔專項（詳見 [Document_Quality_Checklist.md](AISDLC_v0.09/guides/system/quality/Document_Quality_Checklist.md)）

---

## 🏗️ AutoClaude 專案架構

**專案目的**：多步驟 Playbook 自動執行引擎，透過 Claude Code CLI 依序執行開發任務；以狀態機管理流程、重試、Token 限制與錯誤升級。

### 核心目錄結構

```
autoclaude/
├── main.py / __main__.py           # CLI 入口 + Playbook 驗證
├── core/                            # 微核心層
│   ├── kernel.py / kernel_state.py / event_bus.py / hookspec.py / wiring.py
│   ├── orchestration/              # OrchestrationCoordinator（SD_06 W1）
│   ├── ports/                      # Ports 抽象介面 — 數量/清單以下方 [Architecture Snapshot] Port 列表為準
│   └── services/                   # mutation/ + auto_resume.py + _auto_resume_metrics.py
├── infra/                           # 基礎設施層
│   ├── adapters/                   # MinimaxBrain / PtyExecutor / ShellEvaluator /
│   │                               # observability/（SD_08 W4）
│   └── repositories/               # factory.py + 3 後端（File / InMemory / PG）+ Dual
├── plugins/                         # active/靜態清單與計數見 [Architecture Snapshot]（hotkey 條件式註冊）
├── models/                          # Playbook / Decision / Escalation / StepMutation
├── perception/                      # PTY wrapper / StreamReader / hotkey
├── decision/                        # MinimaxClient / PromptBuilder
├── execution/                       # playbook_runner (thin facade) / steps_orchestrator/ /
│                                   # workflow_detector / failure_tracker / convergence_monitor /
│                                   # error_classifier / error_budget / cross_step_validator
├── evolution/                       # PlaybookEvolver（INJECT_STEP / SPLIT_STEP）
└── utils/                           # config / logger / notifier / checkpoint_manager /
                                    # token_tracker / knowledge_base / trace_context（SD_08 W4）

scripts/                              # example_playbook.yaml
tests/                                # plugins/ core/ infra/ contract/ equivalence/
                                      # cli/ integration/ perf/
```

### 新增 Plugin 的 SOP

1. **建立檔案** `autoclaude/plugins/<feature>_plugin.py`（PascalCase 類別名）
2. **繼承 HookSpec**：實作對應 hook（before_step / after_step / on_token_halt / on_escalation 等）
3. **註冊至 wiring**：加入 `_REGISTER_ORDER`，依需要 constructor 注入 ports（**不可直接 import infra**）
4. **撰寫單元測試**：`tests/plugins/test_<feature>.py`，目標 coverage ≥ 90%
5. **LOC 預算**：分級制（ADR-SD07-001）— plugin_entry ≤ 250；超出拆 `<feature>_plugin/` package
6. **禁止反向相依**：Plugin 之間不可互相 import；協作走 EventBus（`.importlinter` Rule 1 阻擋）

### DAL 三後端 storage.mode

| 模式 | 行為 | 適用 |
|------|------|------|
| `yaml_only`（預設） | 純 File backend；零 PG 依賴 | 開發 / 單機 |
| `both` | File 主寫 + PG 影子；`fail_loud / yaml_wins / db_wins` 三策略 | PG 上線灰度 |
| `db_only` | 純 PG backend；YAML 僅供匯入 | Production 穩定後 |

DSN 解析優先級：`AUTOCLAUDE_DB_DSN` > `AUTOCLAUDE_PG_DSN`（deprecated）> `config.storage.db_dsn`。

---

## 📜 Phase 0~6 微核心化重構歷程

- **Phase 0~3**：baseline + `core/`（Kernel+EventBus+HookSpec+Ports）+ `infra/`（adapters+repositories）+ 12 Plugin 拆解
- **Phase 4~6**：PlaybookRunner thin facade（Kernel facade）+ DAL 抽象化（File/InMemory/PG 三後端）+ pgvector HNSW（m=16, ef_construction=64）
- **SD_03 ~ SD_06 完整紀錄**：[sprint_history.md §1.1~§1.4](docs/05_development/sprint_history.md#11-sd_improving_03phase-4-facade-切換) — Facade 切換 / god-object 拆解 / Counter SSOT + TokenGuard 下沉 + Mutation v2 / **PG 三層任務模型 + Brain/Executor 分工**（SD_06 已於 SD_08 W6 滾動下沉 2026-05-18）

> **Production 上線紅線（SD_06 遺留）**：⛔ 真正上線前必須由人類 DBA 在公司 staging（≥ 1M 真實列）重跑 + 人類 PM 親簽 release approval；SD_08 W5 落地 ADR-SD08-005 雙軌制 + pg_health.py WAL lag adapter，**正式啟用延 SD_09**（雙條件：可觀測性 GA + 30 天零 drift）。

### SD_Improving_07（LOC 政策 + 肥胖檔案二度拆 + 6 議題 e2e）— ✅ 全程 G0~G6 完成 2026-05-18

**主軸**：(a) ADR-SD07-001 LOC 分級政策（取消 250 一刀切，分級 150/250/300/400/500 + 絕對紅線 750）；(b) `_impl.py` 736 行拆解（service tier ≤ 500，拆出 `_escalation_handler.py` + `_correction_helpers.py`）；(c) 6 大議題 e2e 整合驗證（Brain/Executor + 三層 CRUD + pgvector real + multi-run resume + ConfigResolver 4 層 property-based）；(d) SD_06 §5 三項物理拔除（`_consecutive_compact_failures` property 5 patch path + `_prepend_global_goal_brief` shim 4 patch path + `PlaybookResult` class → KernelResult factory + property alias 路線）；(e) 14 Plugin walk-through + `runner-no-checkpoint-logic` importlinter Rule 6 升級；(f) token_guard 拆 5 子模組（thresholds/compactor/git_verifier/watcher/policy）；(g) mutation-test-nightly + pg-e2e-nightly CI job 建立（continue-on-error=true 非阻塞）。

**主要 Wave**：W0~W6 共 7 Wave / 28 PD。**G6 末基線**：**2,012 passed / 121 skipped**（2026-05-18）<!-- baseline-ok: SD_07 G6 歷史快照，非現行基線 -->；importlinter **6 kept / 0 broken**；LOC violations=**0**（baseline 永久鎖定 14058）；equivalence **83/83**；NOTE(SD_07)=0。**核心交付**：[SD07_Migration_Guide.md](docs/08_deployment/SD07_Migration_Guide.md) v1.0 + [SD07_Plugin_Audit_Report.md](docs/06_quality/SD07_Plugin_Audit_Report.md) v1.0 + AC Matrix 19 條 + `factory function + property alias` 路線（零 caller 改動）。詳見 [sprint_history.md §1.5](docs/05_development/sprint_history.md)。

### SD_Improving_08（文件治理 + 可觀測性 + mutation/perf baseline）— ✅ 全程 G0~G6 完成 2026-05-18

**主軸**（8 議題群 × 7 Wave / 44 PD，PM 拍板優先順序 A→F→D→C→E→B→G→H）：(A) SD_07 遺留收尾 + (E) CLAUDE.md ≤ 400 + Architecture Snapshot SSOT + sprint_history.md 滾動窗口 N=2（W0）；(F) **可觀測性升級** — IObservabilityPort + LocalLogger adapter + trace_id ContextVar + KB metric 4 項（W4，核心 Wave）；(D) mutation pilot — TokenGuardPlugin 兩週 + 分模組目標 75/70/65%（W3）；(C) AC4 nightly 14 天採集 + `needs-pg-e2e` labeled PR 觸發（W2）；(B) Migration Guide v2 backlog 三項評估 + `_runner_internals` contract 文件化（W1）；(G) 性能 baseline 雙軌 — CI nightly + 季度 perf machine + p95 < 15%（W5）；**(H) PG production SOP 延 SD_09**，SD_08 W5 僅做前置（`pg_health.py` WAL lag adapter + ADR-SD08-005 雙軌制）。

**新增 5 條 ADR**：[ADR-SD08-001](docs/04_planning/ADR/ADR-SD08-001-claude-md-budget.md) CLAUDE.md 治理 / [002](docs/04_planning/ADR/ADR-SD08-002-mutation-baseline.md) mutation 分模組 / [003](docs/04_planning/ADR/ADR-SD08-003-perf-regression-policy.md) perf 告警 / [004](docs/04_planning/ADR/ADR-SD08-004-observability-port.md) IObservabilityPort / [005](docs/04_planning/ADR/ADR-SD08-005-pg-production-dual-track.md) PG 雙軌制。預估 W6 末 ≥ 2,100 passed<!-- baseline-ok: SD_08 規劃期預估值歷史快照，非現行基線 -->。詳見 [SD_Improving_08.md](docs/04_planning/SD_Improving_08.md) v1.0 + [SD08_Execution_Guide.md](docs/05_development/SD08_Execution_Guide.md) v1.0。

**W0~W6 已通過 2026-05-18**（摘要）：W0 CLAUDE.md ≤ 400 + Snapshot SSOT + 5 ADR；W1 v2 backlog 三項決議 + Runner_Internals 防復活柵欄；W2 AC4 nightly collector + progress_check + pg-e2e-on-label；W3 mutation pilot TokenGuard + baseline_lock/mutation_analysis + 11 case contract；W4 核心 IObservabilityPort + LocalLogger + trace_id ContextVar + KB metric 4 項 + Rule 7 + 34 新 case；W5 perf_baseline + 4 場景 perf 測試 + perf_regression_check 三級告警 + perf-baseline-nightly CI + pg_health.py WAL lag adapter + Production_Migration_SOP §1-§3 + ADR-SD08-005；**W6** SD08_Migration_Guide.md v1.0 + AC Matrix 29 條 + 四方審查 + PM 簽核 + SD_06 滾動下沉 §1.4 + SD_Improving_09.md 大綱。

**G6 實測**：≥ 2,100 passed<!-- baseline-ok: SD_08 G6 歷史快照，非現行基線 --> / importlinter 7 kept / 0 broken / LOC=0 / equivalence 83/83。R-SD08-A-1/C-1/D-1/D-2/E-1/F-1/F-2/G-1/H-1/PM-#3~#8 — **全數 CLOSED**。詳見 [gate_audit.md SD08-G0~G6](docs/05_development/gate_audit.md) + [risk_log.md §14](docs/05_development/risk_log.md) + [SD08_Migration_Guide.md](docs/08_deployment/SD08_Migration_Guide.md) v1.0 + [sprint_history.md §1.6](docs/05_development/sprint_history.md)。

### SD_Improving_09（觀察期 #1/#2/#3 採集中 + W3 zero-trust audit 連 25 輪 + R48 四方並行 audit 揪修 R47 殘留 P0「CLAUDE.md 3 行 >800cp 破 contract test」）— 🟡 W0 啟動 2026-05-20

**主軸**：SD_08 三個觀察期由本地 nightly 採集（[`tools/run_local_nightly.ps1`](tools/run_local_nightly.ps1)）；#1 mutation pilot kill_rate ✅ 達標，unique sha 為**源碼演進閘門**（需 W1 改 token_guard 源碼，idle 凍結不達標，ADR-SD09-009 §11.6）；#2 AC4 14 天 p95<60ms tolerant（ADR-SD09-008 v0.4）達標日 **~2026-06-16**（R55 forensic 訂正：原 06-08 投影過樂觀；`ac4_progress_check.filter_recent` 為過去 14 日曆天滾動窗口需 14 連續筆，對 schtasks 漏跑日高度敏感；最後缺口 06-02 → 需 06-03~06-16 連續無缺口，任一漏跑即順延）；#3 drift_log 30 天零 severity≠info 達標日 **~2026-06-24**。詳見 [SD_Improving_09.md](docs/04_planning/SD_Improving_09.md) v1.0。

**最新狀態（improving_101 校正，2026-06-30）**：**ADR-SD09-011 解除 mutation 鎖定的日曆綁定**（掌舵者質疑「空轉一個月」）。根因＝M-05 同 UTC 日去重（`mutation_baseline_lock.py`）+ 每日 nightly → unique sha 每日上限 1、7 個需 ≥7 日曆天、idle 稀釋 → 空轉數週（DEF-101-001 P2 fixed@101）。**修法**：去重鍵 UTC日期→`source_sha256`（`_dedup_key`，同日多 sha 皆計入/同 sha 留最新），unique-sha 累積改由 token_guard 源碼變動觸發（新 `autoclaude-mutation-on-change.yml`+pre-push opt-in），nightly 角色轉 kill_rate 漂移監控/flaky（紀律#6 分軌）；**反作弊不減**（unique sha 守門/0.68 threshold/CONSECUTIVE_RUNS=7 全保留，ADR-SD09-011 §3）。既有 30 筆 history 方案A壓縮（`--migrate-compact-sha`）→ 6 筆/真實 **4 unique sha**，距 7 待 3 次真實 token_guard 演進（隨開發節奏累積、不熬日曆；如 DEF-100-002 L49 重構即+1），最終鎖定/退出仍需 PM 決策。零退化 3618→**3622**/0/122、lint 8 kept、零碰 autoclaude/ 微核心、三鏡 audit PASS。improving_100（殺 token_guard 真缺口 survived + L49 等價變異標記）見 sprint_history.md。


## 📊 模型欄位（核心參考）

### Playbook / PlaybookTask（`autoclaude/models/playbook.py`）

`Playbook` 主要欄位：`version` / `project` / `global_goal`（Gap-011-A，總目標供 Minimax 對齊）/ `workflow_type`（auto / aisdlc / aisdlc_sdd）/ `global_invariants`（max_retries_per_step, auto_compact_interval）/ `context_negotiation` / `tasks`。

`PlaybookTask` 主要欄位：`step_id` / `name` / `prompt` / `command` / `expected_output_regex`（評估前自動 strip ANSI）/ `evaluator_command` / `evaluator_timeout_seconds`（預設 120）/ `max_retries` / `maintain_context`（預設 True，傳 `--continue` 維持對話脈絡）/ `token_guard`（SD_05 W2 per-step override）。

### PlaybookCheckpoint（`autoclaude/utils/checkpoint_manager.py`）

跨 TOKEN_HALT / ESC+F12 / 演化重啟的執行狀態持久化。核心欄位：`playbook_path` / `step_idx` / `step_id` / `total_steps` / `peak_token_pct` / `scheduled_resume_at` / `failure_history`（Gap-007-A）/ `active_step_attempt` / `last_correction_prompt` / `completed_step_ids`（Gap-041/042）/ `goto_counter` / `inject_before_counter` / `skip_to_counter` / `step_evolution_counter`（Gap-042/048，跨 Session 防無限迴圈）/ `run_id` / `goal_task_id`（SD_06 W5）。

### KernelResult（`autoclaude/core/kernel.py`）— SSOT（取代 PlaybookResult）

`success` / `completed_steps` / `total_steps` / `reason` / `step_log` / `completed_step_ids` / `workflow` / `halted`（含 `halt_for_token` property alias）/ `scheduled_resume_at` / `evolved_playbook_path` / `evolution_fresh_required`。SD_07 W4 完成 `PlaybookResult class → KernelResult` factory function 物理拔除。

---

## ⚙️ PlaybookRunner 關鍵行為

- **`dry_run=True`**：跳過 Claude Code 執行，以 regex keyword 合成輸出
- **ANSI strip**：regex 比對前自動 `strip_ansi()`
- **ESCALATION**：超過 `max_retries` 後桌面通知 + `EscalationDump`（含 shell 行動清單）+ `PlaybookEvolver` 嘗試自動演化
- **Token Guard**：≥ 80% `/compact`、≥ 90% 儲存 checkpoint 並排程恢復
- **Checkpoint 續跑**：原子寫入；`--fresh` 忽略 checkpoint 重跑
- **Hotkey 中斷**：ESC+F12 全域安全停止
- **ErrorBudget**：per-error-class 重試上限（syntax:2, assertion:5, environment:0）
- **CrossStepValidator**：步驟切換前以 `git status` 偵測污染（> 5 個修改未確認時警告）
- **Meta-learning**：`FailureKnowledgeBase` 跨 session 記錄成功策略
- **global_goal 對齊（Gap-011-A）**：Minimax 修正 prompt 注入 `## 系統總目標`
- **動態步驟突變（Gap-011-B）**：`REVISE_CURRENT` / `INJECT_AFTER`；門檻 `attempt ≥ 2 && convergence_trend in (stuck/oscillating/cycling)`
- **GOTO 上限可配置（Gap-049）**：`PlaybookConfig.max_goto_per_step` 預設 3
- **跨 Session 計數器持久化（Gap-042/048）**：4 個 counter 寫入 PlaybookCheckpoint，啟動時自動恢復
- **KB 預播種兜底（Gap-045）**：演化後重啟以 `{ErrorClass.IMPORT}:{_PRE_id}:env_setup` 預播種；查詢端主 key 未中時回退兜底 key

---

## 🚀 CLI / 測試 / Playbook 範本

```bash
# CLI
python -m autoclaude <playbook.yaml> [--config config.yaml] [--fresh]
autoclaude <playbook.yaml> --config config.local.yaml

# 全部測試 / 指定模組
python -m pytest tests/ -q
python -m pytest tests/test_playbook_runner.py -v
python -m pytest tests/test_decision.py -v        # MinimaxClient + StepMutation
python -m pytest tests/test_gap009.py -v          # Gap-009 ~ Gap-011 整合驗證

# Mock CLI 本地整合測試
python tests/fixtures/dummy_cli.py                # 配套 tests/fixtures/mock_playbook.yaml
```

### Playbook YAML 範本

```yaml
version: "1.0"
project: "MyProject"
global_goal: |
  建立一個通過所有單元測試的 FastAPI 驗證模組。
global_invariants:
  max_retries_per_step: 3
  auto_compact_interval: 5
tasks:
  - step_id: "T01"
    name: "步驟名稱"
    prompt: |
      給 Claude Code 的詳細 prompt
    expected_output_regex: "\\[DONE\\]"
    evaluator_command: "pytest tests/test_foo.py -v"   # 可選，雙重驗證；shell=True 走平台原生殼（Windows=cmd.exe，非 bash），勿用 POSIX 專屬語法（test/單引號/grep 等）
    evaluator_timeout_seconds: 60                       # 可選，預設 120
    max_retries: 2                                      # 可選，使用全域設定
    maintain_context: true                              # 可選，預設 true
```

---

## 🔴 Nightly / CI 取證紀律（SD_09 W0 教訓 — 防止再犯）

**完整版**：[docs/06_quality/Nightly_Forensic_Discipline.md](docs/06_quality/Nightly_Forensic_Discipline.md) v1.8（19 條）。SD_09 W0~W3 40 輪 audit 累積；違反任一條 → P0 audit。**任何紀律新增 / 修訂必須先改完整版，再同步本摘要**。

1. **stage rc 必須區分「真實失敗」vs「工具標準回報」** — bitmask 工具不可單純 `rc != 0` 判 fail（mutmut：`rc & 1 != 0`）
2. **log 必須含完整統計** — 不信任預設 dump（如 `mutmut results` 缺 Killed → kill_rate=0% 假象）；直查 raw store（sqlite Mutant 表）
3. **PASS 聲稱必須引 RunId log:L 行號** — `logs/nightly_latest.log` 為單一真相，拒絕概括快照表述
4. **驗證鏡子自身要被驗證** — `validate_*` 工具必有單元測試（含假 PASS 場景）；ps1 複雜分支也算
5. **跨工具數字對齊 assertion** — 同來源多 parser 不一致時印 WARN，summary 為單一真相
6. **採集寬鬆 vs 升級嚴格分軌** — 雙 env（採集容忍 + 升級嚴格）；單 env 同時控兩語意即放棄門檻
7. **cache 路徑強制 fresh** — `.mutmut-cache` / `.pytest_cache` / `.ac4_junit.xml` 跑前 `rm -rf`，避免舊資料騙過驗證
8. **載具 .sh 必須 LF 行尾** — Windows autocrlf 轉 CRLF → bash 報錯訊息尾帶「dollar 引號包住反斜線＋小寫 r」逸出字樣（本句刻意全中文描述，防反斜線再遭寫入管道吞掉致本行自身格式毀損——R12 SA-3R 同款根絕法，R13 DOC-5 實證本行原文已毀）；`.gitattributes *.sh text eol=lf` + hook `check_sh_eol.py`
9. **Docker SKIP 跨 stage 一致** — Docker 不可用時所有依賴 stage 同模式 SKIP，禁空殼 if 跳過回 rc=0 偽綠燈
10. **fallback 真實 jsonl 可區分** — `try/except` 後 mock fallback 須寫布林標記欄（如 `emit_real:bool`），拒絕 `=False` 紀錄
11. **latest log pointer 完整 run** — 末段 `Copy-Item` 自當次完整 $Log 寫入，禁 partial buffer；Windows file lock 用 `FileShare.ReadWrite` + retry
12. **mutation history 必含 source_sha256** — tail 7 unique sha ≥ 7，防同 commit 重跑 7 次騙鎖；舊紀錄缺欄位寬鬆通過
13. **觀察期 jsonl 進度可見** — 末段印 `END observation progress: ... (delta=N; stage=R)`；R19 強化 delta 取證明示「未進帳因 stage crash」；R10：mutation 軌分子改 unique-sha（ADR-SD09-011，原始列數會虛報）
14. **schtasks vs 互動 PATH 等價 + StrictMode $null.Property 保護** — ps1 開頭自動補 pyenv-win Scripts；禁 `(Get-Command X -EA SilentlyContinue).<Prop>` 鏈式；改兩步式（R19 P0-AUDIT-R18-1 修復）
15. **呼叫端工具路徑分隔符相容性（Bash 反斜線吞噬根治）** — Bash 工具呼叫 `tools\run_local_nightly.ps1` 時反斜線被 escape 吞噬 → `toolsrun_local_nightly.ps1` 找不到檔案 → exit 127。CLAUDE.md / SOP 範例**一律用正斜線** `tools/run_local_nightly.ps1`；schtasks 用絕對 Windows 路徑；以 PowerShell 工具呼叫亦可（R40 P2-R40-2 修復）
16. **pytest 數字 SSOT 必須註記隨機性與 fixture 前提** — 引用 pytest 數字（如 2,716 passed）時加註「pytest-randomly 未啟用，順序由 collection 確定」<!-- baseline-ok: 紀律敘例之歷史數字，非現行基線站點 -->；pyproject.toml 不安裝 pytest-randomly；引入前需先補測試隔離（R40 P1-R40-1 偽陽性預防）
17. **zero-trust 須雙向：agent audit 結論本身亦須複核** — subagent 聲稱「某檔案不存在」須以 `find`/`rg -l`/`ls` 獨立複核（嚴禁單憑 `fd`，未安裝時靜默回空 → 誤判不存在）；可機械驗證之 finding（檔案存在 / 數字驗算 / 行號）落入 backlog 前主 agent 須親跑複核，誤報與真缺陷同樣留證（R57 SD agent `fd` 誤報 `test_pg_memory_store_security.py:14` 不存在實則存在）
18. **mutation 必須在隔離樹執行，禁止就地突變活體工作樹** — mutmut 就地改寫 volume-mount 源碼會與並行 pytest/audit 互踩產生假紅、kill 時殘留變異；載具須 tar 複製至 container 內 `/tmp/mutwork` 隔離樹（editable install 指向隔離樹），輸出物寫回 `/workspace` 維持取證鏈（Improving_012 Phase 1 QA P1-7）
19. **驗證載具 import 路徑一致性** — 一律從專案 cwd 跑 `python -m pytest`/`python -c`，禁 `python <repo 外路徑>.py`（sys.path 不含 cwd → shadow 至舊 editable 副本）；`local_ci_gate` gate 0 哨兵以 git rev-parse + pathlib **動態比對** `autoclaude.__file__` 位於當前 repo 根之下（不再寫死 `'AISDCL_Agent'` 字串，repo 更名／搬移不誤判）（流程問題 #9b/#9c，Improving_012 Phase 3）

> **採樣統計**：baseline lock 必須 `samples ≥ 20`；< 20 印 warning「statistical noise high; not blocking」；`perf_regression_check.py` baseline samples<20 自動 BLOCK→WARN；rc 三態 0/2/1 = 綠/warn/block；`Invoke-Stage` rc=2 視為 WARN（ADR-SD08-003 §2.6 v1.1）。

## ⚠️ 重要提醒

| ✅ DO | ❌ DO NOT |
|-------|----------|
| 使用繁體中文回覆（專有名詞除外） | 使用英文 / 韓文 / 日文 / 簡體中文回覆 |
| 每支程式開發完立即編譯測試 | 累積開發多支才編譯 |
| 文檔寫入前確認正確目錄 | 文檔寫入錯誤目錄 |
| 遵循 AISDLC ID 命名規範 | 編譯失敗或測試失敗後繼續開發 |
| 文檔交付前執行品質檢查 | 跳過單元測試 / 註解掉失敗的測試 |
| stage rc 反映 process exit code | 用 log validity / regex match 蓋過真實 rc |
| PASS 聲稱引用 RunId log 行號 | 用歷史快照覆蓋 latest log 實況 |
| 採集寬鬆 + 升級嚴格分軌設定 env | 單一 env 同時控制兩種語義 |
| nightly cache 跑前強制 fresh | 容忍舊 cache → 當次 crash 仍假 PASS |

---

## 🪝 Hook 治理（ADR 後續補）

> **哲學**：Claude Code hooks 只能控制 **tool 呼叫** 與 **生命周期事件**；**無法直接改變 LLM 內容生成**。因此 CLAUDE.md 的 prompt-level 規範（語言 / 編譯測試循環 / ID 命名）仍須**保留**，Hook 僅做**補強**與**事後告警**。

**設定檔**：[.claude/settings.json](.claude/settings.json)（hooks 啟用列表）

**目前啟用的 6 個 Hook**（SD_09 W0 後新增 4 個 + W2 nightly audit 後新增 1 個 + ps1 編碼根治 1 個）：

| Hook | 事件 | Script | 動作 |
|------|------|--------|------|
| 語言檢查 | Stop | [check_lang.py](tools/hooks/check_lang.py) | 偵測 assistant 訊息含韓/日/簡體 → stderr warn（exit 1，不阻斷） |
| 文件路徑強制 | PreToolUse(Write) | [enforce_docs_path.py](tools/hooks/enforce_docs_path.py) | `.md` 必須在 `docs/0[1-8]_*/` 或根層白名單；違規 exit 2 阻斷 |
| LOC 預算檢查 | PostToolUse(Edit\|Write) | [loc_budget_check.py](tools/hooks/loc_budget_check.py) | `.py` 超 tier budget → warn；CLAUDE.md > 400 行或單行 > 800 codepoint → exit 2 阻斷（#10a） |
| Snapshot 新鮮度 | Stop | [claude_md_freshness.py](tools/hooks/claude_md_freshness.py) | `snapshot_sync.py --check` drift → warn；CLAUDE.md > 400 行 → exit 2 |
| .sh LF 行尾 | PostToolUse(Edit\|Write) | [check_sh_eol.py](tools/hooks/check_sh_eol.py) | `.sh`/`.bash` 含 CR/CRLF → exit 2 阻斷（紀律 #8 / SD_09 W2 nightly audit） |
| ps1 編碼根治 | PostToolUse(Edit\|Write) | [check_ps1_encoding.py](tools/hooks/check_ps1_encoding.py) | `.ps1`/`.psm1`/`.psd1` 含非 ASCII 且無 BOM → **自動補 UTF-8 BOM**（防 PS5.1 ANSI 亂碼破壞 parser；auto-fix 不阻斷，因 Write 無法產 BOM）。同 wire 於根 `.claude/settings.json` 使 root session 亦生效 |

**Backlog（暫未啟用）**：`build_test_cycle.py`（PostToolUse 每個 py edit 跑測試太慢）、`agent_autoloader.py`（yaml header 注入誤觸發風險高）、`check_id_naming.py`（誤判率高）、`nightly_guard.py`（後續評估）。

**單元測試**：[tests/tools/hooks/](tests/tools/hooks/)（每支 hook ≥ 3 case；SD_09 W0 §4「驗證鏡子自身要被驗證」紀律）。

> **本機 CI 對等（push 前全綠）**：另有 **git hooks**（`tools/git-hooks/` pre-commit/pre-push，`tools/install_git_hooks.ps1` 安裝；有別於上述 Claude Code hooks）+ **act**（`tools/run_act.ps1` 在 Linux 容器跑根層 autoclaude-ci.yml，於 monorepo 根執行）+ **docker-compose.ci.yml**（pg17 對齊 CI）+ **mock_brain_server.py**（本地 LLM mock）。一鍵：`tools/local_ci_gate.ps1`。macOS 對等 `.sh` 載具（`install_git_hooks.sh`／`run_act.sh`／`local_ci_gate.sh`／`run_local_nightly.sh`）完整對照見根層 ONBOARDING.md §6。詳見 [Local_CI_Parity_Guide](docs/08_deployment/Local_CI_Parity_Guide.md)。

---

**文檔元數據**：v7.11 | 建立 2025-01-11 | 最後更新 2026-07-19（權威以 git log 為準） | 適用 AISDLC v0.09+（v7.11：R13 跨平台複審——pytest 基線數字收斂根層 ONBOARDING §7 單一出處（check_pytest_baseline_sites 機械鎖）、AISDLC_v0.09 未入庫註記、ADR 去計數、紀律 8 毀損字樣全中文化。v7.10：R10 跨平台複審——nightly 五變更（sdd-fsm-chaos stage／recall rc [ref] 捕捉／mutmut 驗證失敗 rc=1／Docker 連續 SKIP ≥3 升級 exit 1／END 進度改 unique-sha 分子），紀律完整版連結 v1.6→v1.7；mutation history 壓縮落盤 29→7 筆（DEF-101-148：improving_101 宣稱之方案 A 壓縮實未執行於本機 live 檔）。v7.9：R9 跨平台複審——基線補巢狀 Claude Code session（CLAUDECODE=1）變因註記：該環境下全套為 3,557/206（requires_claude_cli 條件 skip，DEF-101-091，屬預期非退化）；紀律連結 v1.2→v1.6 訂正。歷史 v7.8 以前明細見 [sprint_history.md §1.7.3](docs/05_development/sprint_history.md)）。

<!-- ARCH_SNAPSHOT_BEGIN -->
## [Architecture Snapshot] — 由 tools/snapshot_sync.py 自動生成（請勿手動編輯本區段；以 `python tools/snapshot_sync.py` 重新生成）

### LOC Tiers（ADR-SD07-001 + ADR-SD08-001）
| Tier | Budget | 對應路徑 |
|------|--------|---------|
| data | ≤ 150 | （見 tools/check_loc_budget.py）|
| plugin_entry | ≤ 250 | （見 tools/check_loc_budget.py）|
| strategy | ≤ 300 | （見 tools/check_loc_budget.py）|
| adapter | ≤ 400 | （見 tools/check_loc_budget.py）|
| contract | ≤ 400 | （見 tools/check_loc_budget.py）|
| service | ≤ 500 | （見 tools/check_loc_budget.py）|
| absolute_limit | ≤ 750 | 全域絕對紅線（任何層級不得超）|
| special: CLAUDE.md | ≤ 400 | ADR-SD08-001 文件治理 |

### importlinter Rules（目前 8 kept）
1. Plugins must not import other plugins (use EventBus instead)
2. autoclaude.core (excl. wiring) must not depend on execution or infra layers
3. _runner_internals must not be imported by core or plugins
4. Brain modules must not import Executor modules (use EventBus)
5. Executor modules must not import Brain modules (use EventBus)
6. playbook_runner / strategy modules must not import checkpoint internal modules (use CheckpointPlugin public API)
7. Plugins must not directly import utils.observability helpers (use IObservabilityPort)
8. Plugin must not directly import IKbMetricStore (use FailureKnowledgeBase routing)

### Plugin 列表（18 個 active / 19 個靜態，按 wiring._REGISTER_ORDER）
1. pre_run_validator
2. hotkey
3. cross_step_validator
4. token_guard
5. global_goal_anchor
6. playbook_persistence
7. sdd_governance
8. fast_path
9. notification
10. knowledge_base
11. preference_memory
12. goal_synthesis
13. goal_progress
14. rtm_writeback
15. translation_learner
16. convergence
17. evolution
18. goto_counter
19. checkpoint

### Port 列表（18 個，autoclaude/core/ports/）
- brain
- embedder
- evaluator
- executor
- goal_freeze_gate
- kb_metric_store
- memory_store
- observability
- playbook_repository
- preference_store
- rtm_feedback
- rtm_sink
- spec_source
- state_repository
- tool_invocation
- topology_dashboard
- translation_learning
- vector_search

### DAL 三後端 storage.mode 矩陣（autoclaude/infra/repositories/factory.py）
| Mode | 行為 |
|------|------|
| `yaml_only` | FileStateRepository（單一；零 PG 依賴） |
| `both` | DualStateRepository（File 主寫 + PG 影子；fail_loud/yaml_wins/db_wins） |
| `db_only` | PgStateRepository（單一；YAML 僅供匯入） |

<!-- ARCH_SNAPSHOT_END -->
