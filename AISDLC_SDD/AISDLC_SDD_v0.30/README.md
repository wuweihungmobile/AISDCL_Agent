# AISDLC-SDD v0.01
# AI-assisted Software Development Lifecycle — Spec-First / System Design Document Driven

**框架版本**: v0.01
**建立日期**: 2026-04-12
**最後更新**: 2026-06-12
**基於**: AISDLC v0.09（開發專注版）
**最新發布 Tag**: v2026.06.06-02

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
| **Chaos 有界停機驗收** | ✅ 37 故障情境隨機注入 × 100 輪，bounded_ratio == 1.0 |
| **最新驗收快照** | pytest 1512 passed / 4 skip / 14 subtests passed · 五軌 TLC No error（META 13 distinct 不回歸）· chaos 37 故障情境 bounded · next_free ACT-162 / R-9.38 |
| **本機優先 CI 平價層** | ✅ ADR-001（Accepted 2026-06-11）：Docker 迷你環境 + act + pre-commit/pre-push + Mock/地端LLM；單一真相源 `scripts/ci-gate.sh`（地端綠 ⇒ 雲端綠）；artifact-cleanup 配額治本 + Dependabot 週更 |

> Runtime 演進細節見 [AISDLC_SDD_INIT.md](AISDLC_SDD_INIT.md) 的 Phase D~Y 元件表與 Rule 9 禁止事項清單；
> 完整規則地圖見 [governance/RULES_INDEX.md](governance/RULES_INDEX.md)；CI 平價層決策見
> [docs/02_architecture/adr/ADR-001-local-first-ci-parity.md](../docs/02_architecture/adr/ADR-001-local-first-ci-parity.md)。

---

## 框架組成總覽

| 元件 | 數量 | 說明 |
|------|------|------|
| **Agents** | 26 | 7 core + 19 specialized（含 4 系統級 runtime agent：orchestrator / diagnostic / evaluator / gc；v0.02 +sdd-playbook-compiler） |
| **Scenarios** | 10 | Greenfield / Brownfield / Refactoring / Documentation / DevOps / Integration / Migration / Performance / Security / Testing |
| **Workflows** | 23 | 1 SDD Gate + 8 core + 13 scenario + 1 ADR（另有 4 Runtime 工作流：FSM Engine / Escalation / Context Governor / Self-Evolution） |
| **SDD 模板** | 59 | 56 md + 3 yaml（見下方分類） |
| **CI/CD 規格** | 12 | 9 場景規格 + 3 Runtime 規格（Drift Monitor / Hub Sync / Production Feedback） |
| **Skills** | 42 | 33 繼承強化 + 9 SDD 核心 |
| **參考指南** | 58 | C4、ID 命名、估算、文檔品質等 |
| **Governance 規則** | 38 | Rule 9.x 自動化閉環防護（R-*.yaml） |
| **形式化軌道** | 5 | TLA+/TLC（tools/fsm_runtime/formal/） |

---

## 快速開始（30 秒）

```
1. 載入框架: 讀取 AISDLC_SDD_INIT.md
2. 選擇場景: greenfield / brownfield / refactoring / … （共 10 種）
3. 自動載入: Agent + Workflow + SDD Enhancement（按需載入，初始 ~200 tokens）
4. 開始執行: SOP + SCG 閘門
```

> SessionStart Hook 會自動偵測是否有未完成 Session（`build/reports/abort/CONTEXT-SNAPSHOT-*.md`），
> 若有則進入 Session 恢復流程；否則執行全新 Session 流程。詳見 [AISDLC_SDD_INIT.md](AISDLC_SDD_INIT.md)。

---

## SDD 新增內容

### 59 個 SDD 專屬模板（56 md + 3 yaml）

| 分類 | 數量 | 重點模板 |
|------|------|---------|
| Testing | 19 | RTM, Invariant Test Contract, Contract Test Spec, Chaos Contract |
| Architecture | 13 | As-Is / To-Be SRD, Before/After Arch, Trust Boundary Map, Spec Anchor |
| Deployment | 7 | CI/CD Pipeline, Monitoring, Cutover, Rollback, IaC |
| Requirements | 5 | Invariant Spec, Third-Party API Research |
| ADR | 4 | ADR Template, ADR Index |
| API | 4 | API Compat, Consumer Contract, Migration Contract Map |
| Quality | 3 | Code Quality Baseline, Tech Debt Spec, SDD Compliance Audit |
| Planning | 2 | Gap Analysis, Refactor Plan |
| Build / Development | 2 | Living Doc Strategy 等 |

### 12 個 CI/CD 規格

- **Base Layer**: DocLint + SpecTrace + OpenAPI Validate + RTM Check（全場景通用）
- **9 場景規格**: Greenfield / Brownfield / Refactoring / Migration / Integration / Testing / Performance / Security（各帶專屬閘門）
- **3 Runtime 規格**: Drift Monitor / Hub Sync / Production Feedback

### 6 個核心 Agent SDD 技能增強

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
| Chaos 驗收 | 37 故障情境隨機注入 × 100 輪，bounded_ratio == 1.0 |
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
AISDLC_SDD_v0.01/
├── AISDLC_SDD_INIT.md          # 框架入口（必讀）
├── FILE_DIRECTORY_RULES.md      # 目錄規則
├── README.md                    # 本文件
├── agent/                       # 26 Agents（7 core + 19 specialized；v0.02 +sdd-playbook-compiler）
├── scenarios/                   # 10 場景（含 SDD 增強）
├── workflow/                    # 23 工作流 + 4 Runtime 工作流
├── docs_template/sdd/           # 59 SDD 專屬模板
├── cicd/                        # 12 CI/CD 規格
├── guides/                      # 58 參考指南（含 system/sdd 核心）
├── .claude/                     # skills/（42 Skills）+ hooks/ + settings.json
├── governance/                  # Rule 9.x 規則（38 R-*.yaml）+ RULES_INDEX.md
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
