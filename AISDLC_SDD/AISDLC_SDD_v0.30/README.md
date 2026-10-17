# AISDLC-SDD
# AI-assisted Software Development Lifecycle — Spec-First / System Design Document Driven

> 🔴 **本檔刻意不寫版號與資產計數**（寫死即過期；原標題與標頭曾逐版沿用 `v0.01`、計數停在 2026-06）。
> 版本號、各類資產數量一律見 [FRAMEWORK_STATUS.md](../FRAMEWORK_STATUS.md)（機械生成，ci-gate `--check` 守新鮮）；
> LATEST 現查：`python AISDLC_SDD/scripts/sdd_version.py`。**被訂正的原文逐字保留**：標題「`# AISDLC-SDD v0.01`」、
> 「`**框架版本**: v0.01`」、「`**最後更新**: 2026-06-12`」、「`**最新發布 Tag**: v2026.06.06-02`」。
> 其餘被改寫的原計數與驗收快照（框架組成總覽表、模板分類表、目錄樹註解、chaos 情境數、pytest 快照等）逐字收在
> `EVOLUTION_LOG.md`〈LATEST 修改備忘：整合輪 115／Dev-SDD-DOC 文件面〉。

**框架版本**: 見 [FRAMEWORK_STATUS.md](../FRAMEWORK_STATUS.md)
**建立日期**: 2026-04-12
**最後更新**: 一律現查 `git log -1 --format='%h %ci' -- <本檔路徑>`
**基於**: AISDLC v0.09（開發專注版）
**最新發布 Tag**: 一律現查 `git tag --list --sort=-creatordate`（本檔不寫快照值）

---

## 什麼是 AISDLC-SDD？

AISDLC-SDD 是基於 AISDLC 框架的 **SDD（規格先行 / 系統設計文件驅動）** 擴展，強調：

> **先有規格，後有程式碼。規格即文件，文件即契約。**

### SDD 三大支柱

| 支柱 | 說明 | 核心機制 |
|------|------|---------|
| **Spec-First Gate** | 規格先行閘門 | SCG-0 ~ SCG-6 自動化品質閘門 |
| **Design-as-Doc** | 設計即文件 | ADR、C4 Model、RTM 強制文件化 |
| **Contract-Driven** | 契約驅動 | OpenAPI 3.1 規格凍結後才開始實作 |

---

## 專案現況

| 里程碑 | 狀態 |
|--------|------|
| **SDD 核心轉型（Phase 01~09）** | ✅ 完成（Phase 01-06 核心轉型；Phase 07-09 完整性補強） |
| **Layer 1 Runtime（Phase D~Y）** | ✅ 完成 — 把 Rule 9 從紙上規則升級為 Hook 層強制攔截，演進至 meta⁸ 互遞迴自我擴充 + 具身接地 + 可解釋性視覺化 |
| **形式化驗證** | ✅ 五軌 TLA+/TLC（SDD / COMPOSITION / OPTIMIZATION / META / FLEET）雙源一致 |
| **Chaos 有界停機驗收** | ✅ 多種故障情境隨機注入 × 100 輪，bounded_ratio == 1.0（情境表見 `tools/fsm_runtime/chaos_runner.py`） |
| **驗收數字** | 一律現查，本檔不複寫：`bash AISDLC_SDD/scripts/ci-gate.sh`（PowerShell：`AISDLC_SDD/scripts/ci-gate.ps1`）的輸出；各軌 passed 數的唯一出處＝monorepo 根層 `ONBOARDING.md` §7；下一個可用 ACT／Rule 編號＝`python -m tools.fsm_runtime.id_registry next-act`／`next-rule`（在版本目錄下執行） |
| **本機優先 CI 平價層** | ✅ ADR-001（Accepted 2026-06-11）：Docker 迷你環境 + act + pre-commit/pre-push + Mock/地端LLM；單一真相源 `scripts/ci-gate.sh`（地端綠 ⇒ 雲端綠）；artifact-cleanup 配額治本 + Dependabot 週更 |

> Runtime 演進細節見 [AISDLC_SDD_INIT.md](AISDLC_SDD_INIT.md) 的 Phase D~Y 元件表與 Rule 9 禁止事項清單；
> 完整規則地圖見 [governance/RULES_INDEX.md](governance/RULES_INDEX.md)；CI 平價層決策見
> [docs/02_architecture/adr/ADR-001-local-first-ci-parity.md](../docs/02_architecture/adr/ADR-001-local-first-ci-parity.md)。

---

## 框架組成總覽

| 元件 | 數量 | 說明 |
|------|------|------|
| **Agents** | 見 FRAMEWORK_STATUS.md | core（SDD 強化）＋ specialized；含系統級 runtime agent（orchestrator / diagnostic / evaluator / gc 等）與橋接 agent（sdd-playbook-compiler / sdd-prd-to-playbook） |
| **Scenarios** | 見 FRAMEWORK_STATUS.md | Greenfield / Brownfield / Refactoring / Documentation / DevOps / Integration / Migration / Performance / Security / Testing |
| **Workflows** | 見 FRAMEWORK_STATUS.md（取 `workflow/README.md` 宣稱的 curated 數，非檔數） | SDD Gate ＋ core ＋ scenario-specific ＋ ADR；另有 Runtime 工作流（`workflow/sdd-*/`：FSM Engine / Escalation / Context Governor / Self-Evolution / AutoClaude Bridge 等，以磁碟目錄為準） |
| **SDD 模板** | 見 FRAMEWORK_STATUS.md | md ＋ yaml（分類見下方；各分類數量以 `docs_template/sdd/<分類>/` 磁碟實掃為準） |
| **CI/CD 規格** | 磁碟現查（`cicd/` 下 `*.md`） | 場景規格 ＋ Runtime 規格（Drift Monitor / Hub Sync / Production Feedback） |
| **Skills** | 見 FRAMEWORK_STATUS.md | 繼承強化 ＋ SDD 核心 |
| **參考指南** | 磁碟現查（`guides/` 下 `*.md`） | C4、ID 命名、估算、文檔品質等 |
| **Governance 規則** | 見 FRAMEWORK_STATUS.md | Rule 9.x 自動化閉環防護（R-*.yaml） |
| **形式化軌道** | 見 `tools/fsm_runtime/formal/` | TLA+/TLC（SDD / COMPOSITION / OPTIMIZATION / META / FLEET 各一軌，雙源一致） |

---

## 快速開始（30 秒）

```
1. 載入框架: 讀取 AISDLC_SDD_INIT.md
2. 選擇場景: greenfield / brownfield / refactoring / … （場景清單見上表，數量見 FRAMEWORK_STATUS.md）
3. 自動載入: Agent + Workflow + SDD Enhancement（按需載入，初始 ~200 tokens）
4. 開始執行: SOP + SCG 閘門
```

> SessionStart Hook 會自動偵測是否有未完成 Session（`build/reports/abort/CONTEXT-SNAPSHOT-*.md`），
> 若有則進入 Session 恢復流程；否則執行全新 Session 流程。詳見 [AISDLC_SDD_INIT.md](AISDLC_SDD_INIT.md)。

---

## SDD 新增內容

### SDD 專屬模板（總數見 FRAMEWORK_STATUS.md）

| 分類 | 重點模板（各分類數量以 `docs_template/sdd/<分類>/` 磁碟實掃為準） |
|------|---------|
| Testing | RTM, Invariant Test Contract, Contract Test Spec, Chaos Contract |
| Architecture | As-Is / To-Be SRD, Before/After Arch, Trust Boundary Map, Spec Anchor |
| Deployment | CI/CD Pipeline, Monitoring, Cutover, Rollback, IaC |
| Requirements | Invariant Spec, Third-Party API Research |
| ADR | ADR Template, ADR Index |
| API | API Compat, Consumer Contract, Migration Contract Map |
| Quality | Code Quality Baseline, Tech Debt Spec, SDD Compliance Audit |
| Planning | Gap Analysis, Refactor Plan |
| Build / Development | Living Doc Strategy 等 |

### CI/CD 規格（數量以 `cicd/` 磁碟實掃為準）

- **Base Layer**: DocLint + SpecTrace + OpenAPI Validate + RTM Check（全場景通用）
- **場景規格**: Greenfield / Brownfield / Refactoring / Migration / Integration / Testing / Performance / Security（各帶專屬閘門）
- **Runtime 規格**: Drift Monitor / Hub Sync / Production Feedback

### 核心 Agent 的 SDD 技能增強

| Agent | 新增技能 |
|-------|---------|
| sa-analyst | 逆向規格工程、Gap Analysis、Business Invariants 提取 |
| sd-architect | As-Is C4 生成、ADR Archaeology、Before/After 架構比較 |
| qa-tester | As-Is 測試規格提取、Invariant Test Contract |
| code-analyzer | Tech Debt 規格化、品質基準線 |
| dev-senior | 漸進式重構策略（Strangler Fig / Branch by Abstraction） |
| technical-writer | Living Documentation + ADR 維護 |

---

## Layer 1 Runtime 與 Rule 9 自動化閉環

Phase D 首開 **Layer 1 Runtime Hooks**，將 Rule 9（CLAUDE.md §9 / [governance/](governance/)）從紙上規則升級為
Claude Code Hook 層的**強制攔截**；Phase E~Y 在其上持續加固，形成有界停機的 Agentic 閉環：

| 機制 | 摘要 |
|------|------|
| Retry Budget | SCG 3 / PR 5 / RTM 2 次超限 → ESCALATION |
| Context Budget | 70 / 85 / 90 / 95% 四階；≥95% 停機並產 Context Snapshot |
| FSM Runtime | 唯一合法 FSM 讀寫入口（atomic write + .bak 輪替） |
| Runtime Hooks | `.claude/settings.json` 的 SessionStart / PreToolUse / PostToolUse 強制層 |
| Formal 驗證 | 五軌 TLA+/TLC 雙源一致 + reachable 不污染 |
| Chaos 驗收 | 多種故障情境隨機注入 × 100 輪，bounded_ratio == 1.0 |
| 自我演進防護 | meta⁸ 互遞迴良基停機證書 + 反 Goodhart 對抗分離 + 人類 signoff 棘輪 |

**絕對禁令（違反即停機）** 與各 Phase 子規則 ACT 對照，完整列於 [AISDLC_SDD_INIT.md](AISDLC_SDD_INIT.md)
與 [governance/RULES_INDEX.md](governance/RULES_INDEX.md)。

---

## 本機優先 CI 平價層（ADR-001）

> 決策全文見 repo 根 [docs/02_architecture/adr/ADR-001-local-first-ci-parity.md](../docs/02_architecture/adr/ADR-001-local-first-ci-parity.md)（Accepted 2026-06-11）。

**問題根因**：上雲後 CI 反覆紅燈，稽核確認**並非程式碼錯誤**，而是 ① GitHub Actions
artifact 儲存配額耗盡把通過的 job 判紅、② 多個 cron job 同時 `git push` 回 main 競爭、
③ Node.js 20 action 退役、④ push/PR 完全沒有 workflow 跑離線測試套件。

**對策**：以單一閘門腳本 `scripts/ci-gate.sh`（repo 根）為**唯一真相源**，讓「地端 =
ubuntu-latest」跑同一組檢查，達成 **地端綠 ⇒ 雲端綠**。四支柱：

| 支柱 | 內容 |
|------|------|
| 迷你正式環境 | `docker/Dockerfile.ci`（python:3.11-slim + Java + tla2tools.jar）+ `docker-compose.yml` 的 `ci-runner`，鏡像 ubuntu-latest 消除 Windows/Linux 差異 |
| act 地端跑 Actions | 根層 `.actrc` + `scripts/act-ci.sh`（於 monorepo 根執行），用 Docker 在地端讀根層 `.github/workflows/` 模擬雲端流程 |
| Pre-commit / pre-push 攔截 | 零相依 `.githooks/pre-push`，由 **monorepo 根層 `tools/git-hooks/` dispatcher** 分流呼叫（`scripts/install-hooks` 設 `core.hooksPath`=根層 dispatcher，兩子專案閘門同時生效；pre-commit 框架路徑在 monorepo 下不支援），push 涉及 AISDLC_SDD/ 時自動跑 `ci-gate.sh`，本機過才能 push |
| Mock 與地端 LLM | `llm_backend.py` 新增 `MockBackend`（確定性零外連）與 `LocalOpenAIBackend`（Ollama/vLLM，預設 OFF）；CI 預設 `session` 後端維持 hermetic |

`scripts/ci-gate.sh` 三段閘門：**[1/3]** 離線 pytest（`-m "not chaos"`，含 offline
reachability BFS）→ **[2/3]** `arch_fitness --strict`（structural fail 阻擋、advisory warn
放行）→ **[3/3]** 五軌 TLA+/TLC（`--full-tlc` 啟用，預設由 offline reachability 代驗）。

**Workflow 硬化**：upload-artifact 一律 `continue-on-error` + 降 retention；action 版本升至
Node24 相容；新增 `aisdlc-sdd-ci.yml`
（現位於 monorepo 根層 `.github/workflows/`）在 push(main)/PR 跑離線閘門補缺口；新增
`aisdlc-sdd-artifact-cleanup.yml`（配額長期治本）+ Dependabot（github-actions + pip 每週自動更新）。
**R40 校正**：`aisdlc-sdd-drift-daily.yml`／`aisdlc-sdd-arch-fitness.yml`（nightly-strict）
已改為 `actions/upload-artifact`（90 天保留）取代原本對 v0.01 凍結基線的 commit/push，
`main-push-serialize` concurrency 群組已隨之移除（v0.01 為凍結基線，不應再被 git 回寫）。

---

## 目錄結構

```
AISDLC_SDD_v<LATEST>/            # 讀作「當前最新演化版」；現查：python AISDLC_SDD/scripts/sdd_version.py
├── AISDLC_SDD_INIT.md          # 框架入口（必讀）
├── FILE_DIRECTORY_RULES.md      # 目錄規則
├── README.md                    # 本文件
├── agent/                       # core + specialized Agents（數量見 FRAMEWORK_STATUS.md）
├── scenarios/                   # 場景（含 SDD 增強）
├── workflow/                    # 工作流 + Runtime 工作流（workflow/sdd-*/）
├── docs_template/sdd/           # SDD 專屬模板
├── cicd/                        # CI/CD 規格
├── guides/                      # 參考指南（含 system/sdd 核心）
├── .claude/                     # skills/ + hooks/ + settings.json
├── governance/                  # Rule 9.x 規則（R-*.yaml）+ RULES_INDEX.md
├── tools/fsm_runtime/           # FSM Runtime + 五軌 formal/（TLA+）
├── prompts/                     # 場景指令集與快速啟動指引
├── releases/                    # 框架發布包（v0.01 + CHANGELOG）
├── knowledge/                   # 失敗模式庫 + held-out 對抗語料
├── build/                       # 建置產出（報告/日誌/規劃歸檔）
└── docs/                        # 專案文檔輸出（使用 SDD 時產生）
```

詳見 [FILE_DIRECTORY_RULES.md](FILE_DIRECTORY_RULES.md)

---

## 相關文件

- [AISDLC_SDD_INIT.md](AISDLC_SDD_INIT.md) — 框架初始化 + Phase D~Y Runtime 元件表（必讀）
- [guides/system/sdd/SDD_Core_Principles.md](guides/system/sdd/SDD_Core_Principles.md) — SDD 三大支柱
- [guides/system/sdd/SDD_GUIDE.md](guides/system/sdd/SDD_GUIDE.md) — SDD 快速指引
- [FILE_DIRECTORY_RULES.md](FILE_DIRECTORY_RULES.md) — 完整目錄結構規則
- [workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md](workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md) — SCG 工作流
- [governance/RULES_INDEX.md](governance/RULES_INDEX.md) — Rule 9.x 規則一覽
