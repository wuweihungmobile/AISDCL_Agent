# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **🔴 回覆語言**：本 workspace 下所有對話回覆**必須使用繁體中文**（專有名詞如 AISDLC、SDD、API、Docker、pytest 保持原文）。兩個子專案的 CLAUDE.md 皆以此為 override 級規範，絕不可用英文／簡體／日韓文回覆。

---

## 這是一個「雙專案 monorepo」

monorepo 根目錄（`AISDCL_Agent/`，各機器 checkout 路徑不同）底下是**兩個獨立子專案** + **一層 monorepo 根整合層**（根 `docs/`）。兩子專案各自有一份 override 級的 `CLAUDE.md`，互為姊妹：`AISDLC_SDD` 是**方法論框架**，`AutoClaude` 是能驅動該方法論的**執行引擎**（AutoClaude 的 Playbook `workflow_type` 支援 `aisdlc` / `aisdlc_sdd`）。**根整合層**（根 `docs/`）不屬於任一子專案，承載「兩者深度整合」的迭代計畫——見下方〈🔴 三條改進軌道〉，**勿與子專案內部的改進系列混淆**。

| 子目錄 | 性質 | 權威指引 |
|--------|------|---------|
| [AutoClaude/](AutoClaude/) | Python 3.11+ 應用程式 — Claude Code 多步驟 Playbook 自動執行引擎（微核心 + Plugin 體系 + DAL 三後端） | [AutoClaude/CLAUDE.md](AutoClaude/CLAUDE.md) |
| [AISDLC_SDD/](AISDLC_SDD/) | 規格先行（Spec-First）SDLC 框架 — 以 Markdown 模板／Agent／Workflow 為主 + FSM runtime（Python）+ TLA+ 形式化驗證 | [AISDLC_SDD/CLAUDE.md](AISDLC_SDD/CLAUDE.md) |

### 🔴 進入任一子專案前的第一動作

**先讀該子專案的 `CLAUDE.md`**，再開始工作。兩份子 CLAUDE.md 都宣告其指令 **OVERRIDE Claude Code 預設行為**，內含嚴格的目錄／命名／閘門規範與大量「違反即停機」的禁令（尤其 AISDLC_SDD 的 Rule 9 自動化閉環防護）。本根檔只負責導航，**不重複**子專案的細則。

### ⚠️ 路徑陷阱（務必注意）

子專案的 CLAUDE.md 是在「以自己為根」的前提下撰寫的：
- 它們文件內的相對路徑（如 `docs/05_development/...`、`autoclaude/core/...`）是**相對於該子專案目錄**，不是相對於本 monorepo 根。
- AISDLC_SDD 的 CLAUDE.md 把根稱為 `d:/CursorProject/AISDLC_SDD/`，實際對應到本 repo 的 `AISDLC_SDD/` 子目錄。
- 跑指令前先 `cd` 到正確的子專案目錄。

---

## 🔴 三條改進軌道（迭代方向總圖 — 勿搞錯方向）

> **為何特立此節**：本 repo 的改進/迭代以**軌道① 範本為唯一驅動器**，其下分 **A 協作／B 手腳（AISDLC_SDD）／C 指揮官（AutoClaude）三柱**；軌道②（框架 RFC）是 B 柱下游帳本、軌道③（AutoClaude 內部）是 C 柱工作流帳本——**三者同源於範本，但檔名相似極易混指**（曾有 session 把「整合迭代」誤指向子專案內部的 `SDD_improving_Automation_NN`，方向全錯）。**動工前先用本表對齊「本輪在哪一柱（A/B/C）、下一份檔名是什麼」。**

| 軌道 | 計畫文件（驅動器） | 性質 / scope | 下一份 |
|------|------------------|-------------|--------|
| **① 整合迭代**（AISDLC-SDD × AutoClaude 深度整合，**範本唯一驅動器**） | 根層 [docs/04_planning/AutoSDD_improving_NN.md](docs/04_planning/) | **三軌**（對齊北極星三點：指揮官 AutoClaude × 手腳 AISDLC_SDD × 雙向協作）：**A 軌**＝雙向協作橋接（SDD→Playbook）；**B 軌**＝手腳框架 dogfooding v0.0X 並回流缺陷；**C 軌**＝指揮官 AutoClaude 自身能力（含 SD_09／Improving_NN，2026-06-15 全收納入）。由 [docs/04_planning/AutoSDD_Iteration_Prompt_Template.md](docs/04_planning/AutoSDD_Iteration_Prompt_Template.md) 驅動，每輪四件套（improving_NN + ZeroTrust_Audit_NN + Defect_Log 累積 + 框架改進落 `v0.0(X+1)/`） | `docs/04_planning/` 現存最大號＋1（動工前以 `ls` 實查；本欄不快照具體號次——R13 曾抓到快照 stale 差 100 號） |
| **② 框架內部 RFC**（AISDLC_SDD 自身演進） | `AISDLC_SDD/AISDLC_SDD_v0.01/build/planning/active/SDD_improving_Automation_NN.md` | **①B 軌 dogfooding 的缺陷回流路徑之一**（框架程式/模板/hook 缺陷提案）；是迭代的**下游產物，不是驅動器**。active 為 26 號 | 隨缺陷回流產生（非定期遞增） |
| **③ AutoClaude 內部能力**（＝軌道① 的 **C 軌工作流帳本**） | `AutoClaude/docs/04_planning/AutoClaude_Improving_0NN.md` + `SD_Improving_NN.md` | AutoClaude 自身能力升級（Improving_012＝Agentic 三能力；SD_Improving_09＝PG production／觀察期）。**2026-06-15 起納入整合範本 C 軌（柱①「指揮官」），由 AutoSDD 範本統籌驅動**；本欄檔案降為該柱工作流帳本（沿用 AutoClaude 自身 docs/ 編號與 G0~G6 Gate） | 以 `AutoClaude/docs/04_planning/` 現存最大號與 C 軌帳本現況為準（本欄不快照具體進度——R13 曾抓到快照 stale） |

**鐵律**：
- 要「推進整合 / 開新一輪迭代」→ **走軌道 ①**，複製 `AutoSDD_Iteration_Prompt_Template.md`、續 `AutoSDD_improving_NN`。**絕不**把 `SDD_improving_Automation_NN`（軌道 ②）當迭代計畫。
- 軌道 ② 只在軌道 ①B 軌發現框架缺陷時，作為回流 RFC 帳本使用；缺陷先入根層累積帳本 [docs/06_quality/AutoSDD_Defect_Log.md](docs/06_quality/)。
- 軌道 ③（AutoClaude 自身能力）**自 2026-06-15 起納入軌道① 範本 C 軌（柱①「指揮官」）統籌驅動**（範本定位＝精進 AutoClaude＋AISDLC_SDD＋兩方協作；指揮官 AutoClaude、手腳 AISDLC_SDD）；其 `AutoClaude_Improving_0NN`／`SD_Improving_NN` 檔保留為 C 軌工作流帳本。**防混淆鐵律不變且更重要**：每輪動工前先用本表對齊「本輪在哪一柱（A 協作／B 手腳／C 指揮官）、下一份檔名」，三柱同源不代表可混指。
- 三軌的 `docs/` 都各自獨立編號（01~08）：軌道 ① 用**根層** `docs/`、軌道 ②／③（C 軌帳本）用各**子專案**的 `docs/`（見〈路徑陷阱〉）。

---

## 兩專案共通的工程紀律

兩個子專案明文共享以下規範（細則見各自 CLAUDE.md）：

1. **繁體中文回覆**（見頂部）。AutoClaude 另有 Stop hook `check_lang.py` 事後偵測韓／日／簡體字並 warn。
2. **開發-編譯-測試循環（強制）**：每完成一支程式立即編譯＋跑單元測試，**絕不累積開發**；編譯／測試失敗立即停下修復，禁止跳過或註解掉失敗測試。
3. **文檔目錄編號制**：產出文件寫入 `docs/0[1-8]_*/`（01_requirements ～ 08_deployment）對應子目錄，不可亂放。AutoClaude 以 PreToolUse hook `enforce_docs_path.py` 強制。
4. **規格先行**：寫程式前先有規格／通過閘門（AISDLC_SDD 的 SCG-0~6；AutoClaude 的 G0~G6 Gate）。

---

## AutoClaude — 常用指令與架構

> 完整內容見 [AutoClaude/CLAUDE.md](AutoClaude/CLAUDE.md)。以下指令請在 `AutoClaude/` 目錄下執行。

### 安裝 / 執行

> 🔴 `tools/bootstrap.*` 偵測到 `uv` 時一律用 `uv venv` + `uv pip install` 建置 `.venv`（`dev_start` 預設路徑），這種 venv **內部沒有 `pip` 模組**（`python -m pip` 會報 `No module named pip`，Mac/Windows 四方複審實機驗證重現），故下列指令一律用 `uv pip install`（uv 已安裝時對任何已啟用的 venv皆可用，不論該 venv 是否由 uv 建立）；只有走 `bootstrap` 的傳統 `python -m venv` 回退路徑（未裝 uv）時，才會有 `pip` 模組可直接用 `pip install`。

> 🔴 **R57 修正：extras 一律加單引號 `'.[...]'`**——macOS 預設 shell 是 zsh，未加引號時 zsh 會對 `.[dev,notifications]` 做 filename generation、repo 內無匹配即以 `zsh: no matches found: .[dev,notifications]` **中止整條指令**（uv／pip 根本沒被執行，使用者看到與套件無關的怪錯）；bash 與 PowerShell 下不加引號雖可跑，加引號則三種 shell 皆正確，故統一加。雷區對照見 [ONBOARDING.md](ONBOARDING.md) §5。

```bash
uv pip install -e '.[dev,notifications]'   # 開發環境（pytest, ruff, hypothesis…）
uv pip install -e '.[lint]'                # import-linter（架構約束檢查）
uv pip install -e '.[postgres,pgvector]'   # PostgreSQL + 向量查詢後端（選配）

python -m autoclaude <playbook.yaml> [--config config.yaml] [--fresh]
autoclaude <playbook.yaml> --config config.local.yaml   # 安裝後 entrypoint
```

### 測試 / Lint
```bash
python -m pytest tests/ -q                       # 全套（🔴 基線數字唯一出處＝根層 ONBOARDING.md §7：出廠環境定義、巢狀 session 變因、選配差異皆載於該節，本檔不重複數字）
python -m pytest tests/test_playbook_runner.py -v # 單檔
python -m pytest tests/ -k <substring> -v         # 單一測試
python -m pytest tests/ -m pg_real                # 需 SD07_REAL_PG_E2E_ENABLED=true + PG DSN
PYTHONUTF8=1 lint-imports                          # import-linter（8 kept / 0 broken）
ruff check .                                       # lint（line-length=100, py311；含 E,F,I,UP）
```
- 🔴 上列為 **bash 形態**。PowerShell **沒有** `VAR=value <指令>` 前綴語法，`PYTHONUTF8=1 lint-imports` 照抄會得到 `The term 'PYTHONUTF8=1' is not recognized`；Windows 須寫 `$env:PYTHONUTF8=1; lint-imports`（雙平台完整對照見 [ONBOARDING.md](ONBOARDING.md) §7；DEF-101-513）。
- pytest markers：`pg_real`（真 PG e2e）、`perf`、`benchmark`。
- `pytest-randomly` **未啟用**，順序由 collection 決定。

### 本機 CI 對等 / Nightly（push 前全綠，PowerShell）
```powershell
powershell -ExecutionPolicy Bypass -File tools/install_git_hooks.ps1   # 裝 git hooks
powershell -ExecutionPolicy Bypass -File tools/local_ci_gate.ps1       # 一鍵本機 CI 閘門（鏡像 autoclaude-ci.yml）
powershell -ExecutionPolicy Bypass -File tools/run_act.ps1 -Job test   # act：Linux 容器跑真 CI（於 monorepo 根執行、讀根層 .actrc）
powershell -ExecutionPolicy Bypass -File tools/run_local_nightly.ps1   # nightly 7 stage（local_ci_gate/mutation/pg-e2e/perf/drift/obs/sdd-chaos）
docker compose -f docker-compose.ci.yml up -d                          # CI 對等 PG（pg17）
```
- **macOS/Linux 對等腳本已存在**：AutoClaude 側 `tools/install_git_hooks.sh`、`tools/local_ci_gate.sh`、`tools/run_act.sh`、`tools/run_local_nightly.sh`（mac 薄聚合器，非 .ps1 對等移植）；monorepo 根層另有 `tools/bootstrap.sh` 與 `tools/integration_gate.sh`。完整雙平台對照表見根層 [ONBOARDING.md](ONBOARDING.md) §6。
- git hooks 為**根層 dispatcher**（monorepo 根 `tools/git-hooks/`）：任一支安裝腳本（`.sh`/`.ps1`）執行後**兩子專案閘門同時生效**，裝一次即可（詳見 ONBOARDING.md §6）。
- CI（**根層** `.github/workflows/autoclaude-ci.yml`；兩子專案 workflows 已全數上移 monorepo 根層並加子專案前綴，對照見 ONBOARDING.md §6.1）push 閘門 jobs（另有 nightly jobs 見 workflow 檔）：`test`（pytest + LOC budget + lint-imports）、`claude-md-budget`（CLAUDE.md ≤ 400 行 + snapshot 新鮮度）、`equivalence`、`pg-contract`（**硬閘**；DEF-101-051 補完三層 goal_task_id 接線後由 continue-on-error 轉阻塞）。
- DB migrations：`alembic upgrade head`（同步 DSN／psycopg2；PostgreSQL 17 + pgvector）。

### 架構大圖
**Hexagonal / 微核心**：`core/`（Kernel + EventBus + HookSpec + `ports/` 抽象介面）只依賴 ports；`infra/adapters/` 提供具體實作（MinimaxBrain / PtyExecutor / ShellEvaluator / LocalLogger）；`infra/repositories/` 是 DAL 三後端（File / InMemory / Pg + Dual）；`plugins/` 為橫切關注點，彼此**不可互 import**，協作一律走 EventBus。`execution/playbook_runner.py` 是無業務邏輯的 thin facade。**Plugin／Port 清單與計數一律見 AutoClaude/CLAUDE.md 的機械生成 `[Architecture Snapshot]`**（本檔不重複數字，免漂移——與 AISDLC_SDD 數字指向 FRAMEWORK_STATUS.md 同政策）。

**狀態機閉環**：INIT → PRE_RUN_VALIDATE → EXECUTE(step) →（Token Guard：≥80% `/compact`、≥90% checkpoint）→ EVALUATE →（失敗則 Minimax CORRECTION / 超限則 ESCALATION → MinimaxEvolver→PlaybookEvolver 自演化）→ DONE → GOAL_SYNTHESIS。

**架構約束以 `.importlinter` 8 條 contract 機械強制 + LOC 分級政策**（data ≤150 / plugin_entry ≤250 / strategy ≤300 / adapter ≤400 / contract ≤400 / service ≤500 / 絕對紅線 ≤750；`tools/check_loc_budget.py` 強制）。`CLAUDE.md` 內含自動生成的 `[Architecture Snapshot]` 區段（由 `tools/snapshot_sync.py` 產生，**勿手動編輯**）。

### 新增 Plugin 的 SOP
1. 建 `autoclaude/plugins/<feature>_plugin.py`（繼承 HookSpec，PascalCase 類別）；2. 實作對應 hook；3. 加入 `wiring._REGISTER_ORDER`，相依走 constructor 注入 ports（**禁止直接 import infra**）；4. 寫 `tests/plugins/test_<feature>.py`（coverage ≥ 90%）；5. 遵守 LOC 分級；6. Plugin 間禁止互相 import（走 EventBus）。

---

## AISDLC_SDD — 常用指令與架構

> 完整內容見 [AISDLC_SDD/CLAUDE.md](AISDLC_SDD/CLAUDE.md)。使用框架前**必讀** [AISDLC_SDD/AISDLC_SDD_v0.01/AISDLC_SDD_INIT.md](AISDLC_SDD/AISDLC_SDD_v0.01/AISDLC_SDD_INIT.md)。

這是一個 **~85% Markdown（模板／Agent／Workflow／治理規則）+ ~15% Python runtime** 的框架。

### 結構（各版目錄結構同構；`AISDLC_SDD_v0.01/`＝ci-gate 凍結基線，最新演化版＝ci-gate LATEST，ci-gate 同時測「凍結基線 + LATEST」）
> 🔴 **具體版本號與各類資產計數一律見唯一真相源 [AISDLC_SDD/FRAMEWORK_STATUS.md](AISDLC_SDD/FRAMEWORK_STATUS.md)**（由 `scripts/framework_status_snapshot.py` 自磁碟+權威源生成，ci-gate `--check` 機械守新鮮）。本檔與子 CLAUDE.md **不重複數字**——版本累積亦不再多檔漂移、不靠人工記得改多處。

`agent/`（core + specialized，含數個 `sdd-*` runtime agent）、`scenarios/`、`workflow/`（1 SDD Gate + core + scenario + ADR，另加 FSM/Escalation/Context runtime）、`docs_template/`（SDD 模板＝md + yaml）、`governance/`（`RULES_INDEX.md` + `R-*.yaml`，依 FSM 狀態 lazy-load）、`tools/fsm_runtime/`（FSM 引擎）、`cicd/`、`guides/`、`prompts/`、`.claude/`（hooks + skills）。

### 測試 / 形式化驗證 / 本機 CI 閘門
```bash
# 在 AISDLC_SDD/ 目錄下：
bash scripts/ci-gate.sh              # 本機 CI 閘門：pytest(not chaos, 含 offline reachability BFS) + arch_fitness --strict
bash scripts/ci-gate.sh --full-tlc   # 另跑五軌 TLA+/TLC（需 Java + tla2tools.jar）

# 直接跑 FSM runtime 測試（pytest.ini 位於 AISDLC_SDD_v0.01/，testpaths=tools/fsm_runtime/tests）：
cd AISDLC_SDD_v0.01
python -m pytest tools/fsm_runtime/tests/ -m "not chaos" -q   # PR 閘門（排除 chaos）
python -m pytest tools/fsm_runtime/tests/ -m chaos            # nightly（chaos 標記測試全套；另有 chaos_runner 100 輪 sweep，bounded_ratio==1.0）
python -m tools.arch_fitness.arch_fitness --strict --json arch-fitness.json
bash tools/fsm_runtime/formal/run_tlc.sh                      # TLA+/TLC（自動下載 tla2tools.jar）
```
- pytest markers：`chaos`（慢；PR 排除、nightly 必跑）、`tlc`（需 `SDD_RUN_TLC=1` + Java）。
- CI 依賴鎖版於 `AISDLC_SDD_v0.01/requirements-ci.txt`（`pyyaml==6.0.3`、`pytest==9.1.1`）以確保「地端 = Docker = ubuntu-latest」同版。

### 框架運作大圖
**FSM 驅動的閉環治理**：`tools/fsm_runtime/` 是 `SDD_FSM_ENGINE.md` 的可執行狀態機。`governance/` 的 `R-*.yaml` 規則（條數見 FRAMEWORK_STATUS.md）由 `rule_loader.load_for_state()` 依當前 FSM 狀態 lazy-load；`.claude/hooks/`（`session_start.py`、`context_ledger_pre/post.py`、`post_commit_drift.py`）在 session／tool／commit 各層注入守門。違反規則 = 破壞 FSM invariant → ESCALATION 或被 hook 攔下。**五軌 TLA+/TLC**（SDD_FSM / META_FSM / COMPOSITION_FSM / OPTIMIZATION_FSM / FLEET_FSM）以形式化方法證明有界停機；改 `_HAPPY_PATH` 必須同步 `formal/SDD_FSM.tla` 並重跑 TLC。

**SDD 三支柱與 SCG 閘門**：Spec-First Gate（規格先於實作）、Design-as-Doc（決策有 ADR、架構有 C4）、Contract-Driven（OpenAPI 凍結後才實作）。SCG-0~6 閘門逐關卡管需求／設計／架構／契約／PR／RTM／發布；標 🔴 的人工確認點不可自動跳過。

**模板使用規則**：`docs_template/sdd/` 的模板**不可直接改**；複製到 `docs/` 對應編號子目錄後再填寫。

---

## 各專案權威文件快查

| 主題 | 文件 |
|------|------|
| AutoClaude 開發規範 / 模型欄位 / Architecture Snapshot | [AutoClaude/CLAUDE.md](AutoClaude/CLAUDE.md) |
| AutoClaude Sprint 脈絡 / ADR / Nightly 取證紀律 | `AutoClaude/docs/05_development/sprint_history.md`、`AutoClaude/docs/04_planning/ADR/`、`AutoClaude/docs/06_quality/Nightly_Forensic_Discipline.md` |
| AISDLC_SDD 框架入口 / 目錄規則 | [AISDLC_SDD/AISDLC_SDD_v0.01/AISDLC_SDD_INIT.md](AISDLC_SDD/AISDLC_SDD_v0.01/AISDLC_SDD_INIT.md)、`AISDLC_SDD/AISDLC_SDD_v0.01/FILE_DIRECTORY_RULES.md` |
| AISDLC_SDD 治理規則總覽（條數見 FRAMEWORK_STATUS.md） | `AISDLC_SDD/AISDLC_SDD_v0.01/governance/RULES_INDEX.md` |

---

## 12-Rule Template（全域工作規則）

These rules apply to every task in this project unless explicitly overridden.

Bias: caution over speed on non-trivial work. Use judgment on trivial tasks.

### Rule 1 — Think Before Coding
- State assumptions explicitly. If uncertain, proceed with the most reasonable assumption and surface it — never guess silently.
- Present multiple interpretations when ambiguity exists, then pick one and say why.
- Push back when a simpler approach exists.

### Rule 2 — Simplicity First
- Minimum code that solves the problem. Nothing speculative.
- No features beyond what was asked. No abstractions for single-use code.
- Test: would a senior engineer say this is overcomplicated? If yes, simplify.

### Rule 3 — Surgical Changes
- Touch only what you must. Clean up only your own mess.
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor what isn't broken. Match existing style.

### Rule 4 — Goal-Driven Execution
- Define success criteria. Loop until verified.
- Don't follow steps. Define success and iterate.
- Strong success criteria let you loop independently.

### Rule 5 — Use the model only for judgment calls
- Use me for: classification, drafting, summarization, extraction.
- Do NOT use me for: routing, retries, deterministic transforms.
- If code can answer, code answers.

### Rule 6 — Token budgets are not advisory
- Per-task: 4,000 tokens. Per-session: 30,000 tokens.
- If approaching budget, summarize and start fresh.
- Surface the breach. Do not silently overrun.

### Rule 7 — Surface conflicts, don't average them
- If two patterns contradict, pick one (more recent / more tested).
- Explain why. Flag the other for cleanup.
- Don't blend conflicting patterns.

### Rule 8 — Read before you write
- Before adding code, read exports, immediate callers, shared utilities.
- "Looks orthogonal" is dangerous. If unsure why code is structured a way, ask.

### Rule 9 — Tests verify intent, not just behavior
- Tests must encode WHY behavior matters, not just WHAT it does.
- A test that can't fail when business logic changes is wrong.

### Rule 10 — Checkpoint after every significant step
- Summarize what was done, what's verified, what's left.
- Don't continue from a state you can't describe back.
- If you lose track, stop and restate.

### Rule 11 — Match the codebase's conventions, even if you disagree
- Conformance > taste inside the codebase.
- If you genuinely think a convention is harmful, surface it. Don't fork silently.

### Rule 12 — Fail loud
- "Completed" is wrong if anything was skipped silently.
- "Tests pass" is wrong if any were skipped.
- Default to surfacing uncertainty, not hiding it.
