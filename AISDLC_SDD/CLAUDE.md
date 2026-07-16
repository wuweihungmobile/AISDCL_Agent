# CLAUDE.md
# Claude Code 專案指導文件 — AISDLC-SDD Framework

**專案**: AISDLC-SDD（AI 輔助軟體開發生命週期 — 規格先行版）
**框架版本**: AISDLC-SDD v0.01（ci-gate 凍結基線）｜**最新演化版**: ci-gate LATEST（`sort -V | tail -1` 動態取最高、實際承載框架演化的「可修改版本」；具體版本號見 `FRAMEWORK_STATUS.md`；各版結構同構）
**基於**: AISDLC v0.09（開發專注版）
**最後更新**: 2026-06-05（標頭）；版本狀態註記 2026-06-22
**SDD 轉型狀態**: ✅ Phase 01~09 全部完成（Phase 01-06: SDD 核心轉型 2026-04-14；Phase 07-09: 完整性補強 2026-04-16）

> **🔴 版本狀態（2026-06-22 校正，免再漂移）**：`AISDLC_SDD_v0.01/` 是 **ci-gate 凍結基線**（恆測、回歸防護，**不可在原地修改**），最新演化版＝ci-gate LATEST（`sort -V | tail -1` 動態取最高版，具體版本號見 `FRAMEWORK_STATUS.md`，免寫死於本檔再漂移）。**框架改動一律走 Copy-on-Evolve**（複製 LATEST → `v0.0(X+1)/` 後於新版修改，絕不原地改凍結版）。下方 Rule 2 目錄表以 `v0.01` 路徑書寫，因**各版目錄結構同構**故仍為有效的版面參考；實際寫入版本依當輪 Copy-on-Evolve 目標版而定。**各類資產數量與最新版本號一律見唯一真相源 [`FRAMEWORK_STATUS.md`](FRAMEWORK_STATUS.md)**（`scripts/framework_status_snapshot.py` 自磁碟+權威源生成、ci-gate `--check` 機械守新鮮）——本檔不重複數字，版本累積亦不再多檔漂移。

> **🔴 重要**：此文件中所有指令 **OVERRIDE** Claude Code 預設行為，必須嚴格遵守。

---

## 🔴 Rule 1：溝通語言規範（強制）

**所有執行過程中的回覆，必須使用繁體中文。**

| 類型 | 規則 |
|------|------|
| 任務回覆、狀態更新 | ✅ 繁體中文 |
| Todo 任務描述 | ✅ 繁體中文 |
| 文檔標題 | ✅ 可中英並列 |
| 專有名詞 | ✅ 保持原文（AISDLC, SDD, Workflow, Agent, SOP, YAML, SCG, ADR, RTM, C4） |

```
✅ 正確：「已完成，共修改 3 個檔案」
❌ 錯誤：「Done! I modified 3 files.」
```

---

## 🔴 Rule 2：專案目錄結構（強制）

### 工作目錄說明

```
d:/CursorProject/AISDLC_SDD/          ← 專案根目錄
├── CLAUDE.md                          ← 本文件
├── AISDLC_SDD_v0.01/                  ← 🔴 SDD 框架目錄（ci-gate 凍結基線；最新演化版＝ci-gate LATEST，版本號見 FRAMEWORK_STATUS.md / 上方版本狀態）
│   ├── AISDLC_SDD_INIT.md             ← 框架入口（使用前必讀）
│   ├── FILE_DIRECTORY_RULES.md        ← 完整目錄規則
│   ├── AISDLC_SDD_UPGRADE_SOP.md      ← 框架升版 SOP
│   ├── AISDLC_SDD_UPGRADE_CHECKLIST.md← 升版前完整檢查清單
│   ├── guides/system/sdd/SDD_Core_Principles.md  ← SDD 核心原則
│   ├── guides/system/sdd/SDD_GUIDE.md ← SDD 快速指引
│   ├── agent/                         ← core + specialized agents（含 sdd-* 系統級 runtime agent，多 sdd-playbook-compiler；數量見 FRAMEWORK_STATUS.md）
│   ├── scenarios/                     ← 場景（greenfield/brownfield/refactoring/documentation/devops/integration/migration/performance/security/testing）
│   ├── workflow/                      ← 工作流（1 SDD Gate + core + scenario + ADR）
│   ├── docs_template/                 ← 文檔模板（含 SDD 專屬模板：md + yaml）
│   ├── cicd/                          ← SDD CI/CD 規格
│   ├── guides/                        ← 參考指南
│   ├── .claude/skills/                ← Claude Code Skills（繼承強化 + SDD 核心）
│   ├── prompts/                       ← 場景指令集與快速啟動指引
│   ├── releases/                      ← 框架發布包（v0.01 tar.gz + sha256）
│   ├── tools/                         ← 工具腳本
│   ├── build/                         ← 建置產出（報告/日誌/規劃歸檔）
│   └── docs/                          ← 🔴 專案文檔輸出（使用 SDD 時產生）
├── AISDLC_v0.09/                      ← 舊版框架（保留參考，不直接修改）
└── docs/                              ← 本框架專案文檔（框架自身的 SDD 產出）
```

### 🔴 寫檔前必須確認位置

**框架層（Layer 2）— 寫入 `AISDLC_SDD_v0.01/` 子目錄**：

| 要寫的內容 | 正確路徑 |
|-----------|---------|
| Agent 更新 | `AISDLC_SDD_v0.01/agent/core/` 或 `specialized/` |
| Workflow | `AISDLC_SDD_v0.01/workflow/core/` 或 `scenario-specific/` |
| 場景 SOP/Enhancement | `AISDLC_SDD_v0.01/scenarios/{scenario}/` |
| SDD 框架模板 | `AISDLC_SDD_v0.01/docs_template/sdd/{category}/` |
| CI/CD 規格 | `AISDLC_SDD_v0.01/cicd/` |
| 分析報告 | `AISDLC_SDD_v0.01/build/reports/analysis/` |
| 階段報告 | `AISDLC_SDD_v0.01/build/reports/phase/` |
| 規劃文件 | `AISDLC_SDD_v0.01/build/planning/active/` |
| 歸檔文件 | `AISDLC_SDD_v0.01/build/planning/archive/` |

**專案層（Layer 3）— 寫入 `AISDLC_SDD_v0.01/docs/` 子目錄**：

| 文件類型 | 正確路徑 |
|---------|---------|
| PRD / FRD / Invariant Spec / Third-Party API Research | `docs/01_requirements/` |
| SRD / C4 / ADR / As-Is / To-Be / Trust Boundary Map | `docs/02_architecture/` |
| ADR 檔案 | `docs/02_architecture/adr/` |
| API 規格 / Compat / Consumer Contract | `docs/02_architecture/api/` |
| Migration Contract Map | `docs/02_architecture/migration/` |
| RTM / Test Plan / Test Strategy / Defect Classification | `docs/03_testing/` |
| Invariant Test Contract / Contract Test Spec / Chaos Contract | `docs/03_testing/contracts/` |
| Gap Analysis / Refactor Plan | `docs/04_planning/` |
| Performance Baseline Spec（PBS） | `docs/04_planning/performance/` |
| Living Doc Strategy | `docs/05_development/` |
| Code Quality Baseline / Tech Debt Spec | `docs/06_quality/` |
| SAD / STRIDE / Compliance Matrix / Asset Inventory | `docs/06_quality/security/` |
| UI/UX / Database Design | `docs/07_design/` |
| CI/CD Pipeline / Monitoring / Release Notes / Cutover / Rollback | `docs/08_deployment/` |
| IaC Specifications | `docs/08_deployment/iac/` |

**❌ 絕對禁止**：
- 寫入 `/tmp/`、`/var/`、系統目錄
- 在框架版本根目錄（`AISDLC_SDD_v0.01/`）直接建立臨時檔案
- 修改 `AISDLC_v0.09/` 的任何檔案（僅供參考）

---

## 🔴 Rule 3：SDD 框架使用規則

### 框架初始化

使用任何 SDD 功能前，必須先讀取：
```
AISDLC_SDD_v0.01/AISDLC_SDD_INIT.md
```

### SDD 三大支柱（必須遵守）

| 支柱 | 規則 |
|------|------|
| **Spec-First Gate** | 規格文件必須在實作前完成並通過 SCG 閘門 |
| **Design-as-Doc** | 每個技術決策必須有對應 ADR；架構必須有 C4 圖 |
| **Contract-Driven** | OpenAPI 規格凍結後才能開始後端實作 |

### SCG 閘門（不可跳過）

| Gate | 時機 | 強制文件 |
|------|------|---------|
| SCG-0 | 需求凍結前 | PRD + FRD 完整性 |
| SCG-1 | 設計凍結前 | SRD + API Spec |
| SCG-2 | 架構凍結前 | C4 圖 + ADR |
| SCG-3 | 開發啟動前 | OpenAPI 3.1 凍結 |
| SCG-4 | PR Review | 實作與規格一致性 |
| SCG-5 | 交付前 | RTM 100% 覆蓋 |
| SCG-6 | 發布前 | 所有閘門通過 |

### 場景對應

| 場景 | SDD 增強 | 必讀 |
|------|---------|------|
| Greenfield | 全新專案 | `scenarios/greenfield/SDD_GREENFIELD_ENHANCEMENT.md` |
| Brownfield | 逆向規格工程 | `scenarios/brownfield/SDD_BROWNFIELD_ENHANCEMENT.md` |
| Refactoring | 系統重構 | `scenarios/refactoring/SDD_REFACTORING_ENHANCEMENT.md` |
| Documentation | 文件維護 | `scenarios/documentation/SDD_DOCUMENTATION_ENHANCEMENT.md` |
| DevOps | CI/CD 規格驅動 | `scenarios/devops/SDD_DEVOPS_ENHANCEMENT.md` |
| Integration | API Contract 驅動 | `scenarios/integration/SDD_INTEGRATION_ENHANCEMENT.md` |
| Migration | 遷移規格先行 | `scenarios/migration/SDD_MIGRATION_ENHANCEMENT.md` |
| Performance | PBS Gate 驅動 | `scenarios/performance/SDD_PERFORMANCE_ENHANCEMENT.md` |
| Security | STRIDE 威脅模型驅動 | `scenarios/security/SDD_SECURITY_ENHANCEMENT.md` |
| Testing | Contract 覆蓋驅動 | `scenarios/testing/SDD_TESTING_ENHANCEMENT.md` |

### SDD 模板使用規則

使用 SDD 模板前，從 `docs_template/sdd/` 取得對應模板，**複製到 `docs/` 下填寫**，不可直接修改模板本身：

```
框架模板（不修改）:  AISDLC_SDD_v0.01/docs_template/sdd/architecture/AS-IS-SRD-TEMPLATE.md
產出文件（填寫）:   AISDLC_SDD_v0.01/docs/02_architecture/AS-IS-SRD-{SystemName}.md
```

---

## 🔴 Rule 4：開發-編譯-測試循環（強制）

**原則：每完成一個功能單元，立即編譯+測試，絕不累積。**

```
開發 → 編譯
  ↓ 失敗 → 立即修復 → 重新編譯
  ↓ 通過
執行單元測試
  ↓ 失敗 → 依規格修復 → 重新測試
  ↓ 通過
繼續下一個功能
```

**❌ 禁止行為**：
1. 累積多個功能後才編譯
2. 編譯失敗後繼續開發其他部分
3. 跳過單元測試
4. 測試失敗後註解掉測試繼續開發

---

## 🔴 Rule 5：檔案命名規範

| 類型 | 格式 | 範例 |
|------|------|------|
| 框架模板 | `{TYPE}-TEMPLATE.md` | `AS-IS-SRD-TEMPLATE.md` |
| 專案文件 | `{TYPE}-{SystemName}.md` | `AS-IS-SRD-OrderSystem.md` |
| ADR | `ADR-{NNN}-{kebab-title}.md` | `ADR-001-use-postgresql.md` |
| API 規格 | `API_{Module}_{Endpoint}.md` | `API_Order_CreateOrder.md` |
| Agent | `{NN}.{role}-zh.yaml` | `04.sa-analyst-zh.yaml` |
| 報告 | `{TOPIC}_{TYPE}.md` | `Phase01_REPORT.md` |

**❌ 禁止**：中文檔名、縮寫不明的命名（`arch.md`、`sprint1.md`）

---

## 🔴 Rule 6：Agent 使用規則

### 核心 Agent（SDD 強化）

| Agent | 角色 | SDD 新增技能 |
|-------|------|------------|
| `04.sa-analyst-zh.yaml` | SA 分析師 | 逆向規格工程、Gap Analysis、Invariants 提取 |
| `05.sd-architect-zh.yaml` | SD 架構師 | As-Is C4、ADR Archaeology、Before/After 比較 |
| `07.qa-tester-zh.yaml` | QA 測試師 | As-Is 測試規格、Invariant Test Contract |
| `code-analyzer-zh.yaml` | 代碼分析 | Tech Debt 規格化、品質基準線 |
| `dev-senior-zh.yaml` | 資深開發 | Strangler Fig / Branch by Abstraction |
| `technical-writer-zh.yaml` | 技術寫作 | Living Documentation、ADR 維護 |

### 場景專屬 Specialized Agent

| Agent | 適用場景 |
|-------|---------|
| `qa-mobile-tester-zh.yaml` | Mobile 測試 |
| `qa-web-tester-zh.yaml` | Web 測試 |
| `sd-mobile-architect-zh.yaml` | Mobile 架構設計 |
| `sd-web-architect-zh.yaml` | Web 架構設計 |
| `performance-engineer-zh.yaml` | Performance PBS Gate |
| `security-engineer-zh.yaml` | STRIDE 威脅模型 |
| `devops-engineer-zh.yaml` | IaC 規格、Pipeline |
| `integration-specialist-zh.yaml` | CDC、OpenAPI First |

> 完整 Agent 配置與載入規則見 `AISDLC_SDD_INIT.md` 的 `auto_load_config`（agent 數量見 FRAMEWORK_STATUS.md）。

### Agent 載入規則

1. 使用前讀取 `AISDLC_SDD_INIT.md` 的 `auto_load_config`
2. 根據場景自動載入 Primary Agents
3. Supporting Agents 按需載入（不預先全部載入）
4. 核心 Agent 文件：`AISDLC_SDD_v0.01/agent/core/*-zh.yaml`

---

## 🔴 Rule 7：ID 命名規範

| ID 類型 | 格式 | 說明 |
|---------|------|------|
| Feature | `F-XXX` | 功能需求 |
| Non-Functional | `NFR-XXX` | 非功能需求 |
| Epic | `EPIC-XXX` | 史詩 |
| User Story | `US-XXX` | 用戶故事 |
| Acceptance Criteria | `AC-XXX-Y` | 驗收標準 |
| API Endpoint | `API-XXX` | API 端點 |
| Test Case | `TC-XXX-Y-Z` | 測試案例 |
| Business Invariant | `INV-XXX` | 不變量（Refactoring 必用） |
| Tech Debt | `TD-XXX` | 技術債（Brownfield 必用） |
| Architecture Decision | `ADR-NNN` | 架構決策 |

---

## 🔴 Rule 8：Human 確認點規範

所有工作流中標記 🔴 的確認點，**必須等待人工確認後才能繼續**，不可假設通過。

**典型確認點**：
- SCG 閘門通過確認
- Before Architecture 凍結確認
- Business Invariants 清單確認
- API Contract 凍結確認
- 規格文件凍結確認

---

## 🔴 Rule 9：自動化閉環防護規則（憲法摘要）

> **🔴 重要**：完整 Rule 9 細則已結構化於 `AISDLC_SDD_v0.01/governance/rules/R-*.yaml`，
> 由 `rule_loader.load_for_state()` 依當前 FSM 狀態 lazy-load；SessionStart hook
> （`.claude/hooks/session_start.py`）會自動注入當前狀態命中的規則。完整地圖見
> `governance/RULES_INDEX.md`（`R-*.yaml` 規則一覽＝R-9.x + R-SELF-STRIDE；條數見 FRAMEWORK_STATUS.md）。
>
> 本節僅保留**永遠生效、違反即停機的絕對禁令**（憲法層）。各 Phase 子規則、ACT 對照、
> 相關文件與驗收憑證一律見對應 `R-*.yaml`。

以下規則確保 SDD Agentic 閉環具備有界停機能力，防止無限重試耗盡 Token。

### 絕對禁令（不可違反，違反即停機）

1. 繞過 `FSMRuntime` 直接讀寫 `FSM-STATE-*.yaml`（R-9.6）
2. 停用 / 刪除 `.claude/` 的 Phase D·E hooks（R-9.6）
3. IMPLEMENTATION 期間 Write/Edit `docs/01~03` 規格文件（R-9.6）
4. SCG/PR/RTM retry 超上限仍重試、不進 ESCALATION（R-9.1）
5. Token ≥ 95% 仍工作、不產 Context Snapshot（R-9.2）
6. 進入 ESCALATION / ESCALATION_FINAL 後自動恢復（必須等人工）（R-9.5、R-9.14）
7. 對 `category=structural` 的 ESCALATION 強行 auto-recovery（R-9.14）
8. 修改 `_HAPPY_PATH` 但不同步 `formal/SDD_FSM.tla`（R-9.18）
9. 把觀測狀態放入 Terminals 集合（R-9.18）
10. 讓 `proposed` / `external` 規則阻塞 SCG（R-9.11）
11. 自動退役 active 規則而不經 `set_maturity(reviewed_by=)`（R-9.20）
12. 自動套用 spec patch 改 FRD/AC 而不經 HUMAN_PENDING（R-9.22）
13. planner 自動選定最高 ROI 目標、繞過 `BACKLOG_PRIORITIZED` 人工 signoff，或 localizer 自動改 spec（R-9.23）
14. 繞過 `meta_halt_monitor` 採納/退役規則、無 capability-delta 重新學回退役指紋（add↔retire 抖動）、或 `EXPERIMENT_REPLAY` 命中率自動 approve 補丁（R-9.24）
15. `intent_composer` 自動 commit 跨意圖排程繞過 `BACKLOG_PRIORITIZED` 人工 signoff、`COMPOSITION_FSM` 併入單軌污染 reachable、跨意圖協商無上限 livelock、或讓 `capability_trajectory_monitor`/`scaffold_ceiling_detector` 的 plateau/ceiling 訊號自動觸發典範轉移或自動退役仍在 fire 的鷹架（R-9.25）
16. `composition_optimizer` 搜尋無上限指數爆炸（超 `SDD_OPT_NODE_BUDGET` 不停）、自動 commit 排程繞過 `BACKLOG_PRIORITIZED`、謊報 proven-optimal（預算耗盡仍稱最優）、或 `OPTIMIZATION_FSM` 併入單軌污染 reachable（R-9.26）
17. `objective_tuner` 自動 commit / 自寫 `composition_objective_scorer` 權重常數繞過人工 `OBJECTIVE_PROFILE_VERSION` bump、用 scorer 自評分數充當 capability-delta tier（Goodhart 自評放水）、tuner 讀寫/影響 held-out 現實代理語料（破對抗分離）、obj-profile 採納退役繞過 `meta_halt_monitor` 或無 capability-delta re-adopt、候選權重搜尋超 `SDD_OBJ_TUNE_BUDGET` 仍指數展開、或把 obj-profile 元迴圈併入單軌 `SDD_FSM.tla` 污染 reachable（R-9.27）
18. 任一 scorer tuner 自動 commit / 自寫評分器權重常數繞過人工 `*_PROFILE_VERSION` bump、用 per-scorer 自評或單獨 oracle 結果充當「聯合 capability-delta tier」（接縫 Goodhart 自評放水）、任一 tuner 讀寫/影響 `knowledge/held-out-corpus/` 聯合 oracle 語料（破對抗分離）、8 命名空間採納退役繞過 `meta_halt_monitor` 或忽略 `CrossScorerChurnBounded` 聚合速率/放任 A→B→A 耦合震盪不升 `MFSM_ESCALATION`、任一 tuner 候選搜尋超 `SDD_CALIB_TUNE_BUDGET` 仍指數展開、一週期同時 bump > K 個評分器一次改整套價值系統（破 `NoBigBangValueRewrite`）、或把 calibration 元迴圈併入單軌 `SDD_FSM.tla`／新增第六軌污染五軌 reachable（R-9.28）
19. `value_dimension_registry` 自動納入新維度 / 自寫維度集合常數繞過人工 signoff + `guard_dimension_expansion`、用 proposer 自評 / 自算覆蓋率充當「維度必要性 capability-delta tier」（維度 Goodhart 自評放水）、proposer 讀寫 / 影響 / import 維度必要性 held-out 語料或評估器（破對抗分離）、value-dimension 採納退役繞過 `meta_halt_monitor` 或忽略 `DimensionCardinalityBounded` stock 天花板而無界增維 / 退役維度無 necessity capability-delta 地 re-adopt（維度震盪繞過棘輪）、候選維度搜尋超 `SDD_DIM_PROPOSE_BUDGET` 仍指數展開、一週期同時新增 > K_dim 條維度一次劫持整個本體論（破 `NoUnboundedOntologyExpansion`）、或把 value-dimension 元迴圈併入單軌 `SDD_FSM.tla`／新增第六軌污染五軌 reachable（R-9.29）
20. `dimension_semantics_synthesizer` 自動納入自我發明維度 / 自寫常數繞過人工 signoff + `guard_dimension_expansion`／`guard_dimension_swap`、用 synthesizer 自評 / 自算覆蓋率充當「自我發明必要性 capability-delta tier」（自我發明 Goodhart 自評放水）、自我發明 probe 自指（引用保留自指 / proposer / oracle 內部信號繞過 `self_reference_guard` 反自利）、synthesizer 讀寫 / 影響 / import `knowledge/held-out-corpus/INV-*` feature 必要性語料或 `dimension_necessity_oracle`（破對抗分離）、自我發明搜尋超 `SDD_DIM_INVENT_BUDGET` 仍指數展開（破有界生成文法，「候選池外」≠「無界」）、retire-to-swap 入軸 tier 未嚴格 > 出軸 tier + `SDD_DIM_SWAP_MARGIN`（A↔B↔A 維度震盪繞過單調價值棘輪）、聚合 swap 速率超 `SDD_DIM_SWAP_RATE_MAX` 仍定基數旋轉重寫本體論（繞過 cardinality stock + per-fingerprint churn）、一週期同時自我發明 > K_dim 條維度 / 多次 swap 一次劫持本體論（破 `NoUnboundedSelfInvention`）、或把 self-invention / swap 元迴圈併入單軌 `SDD_FSM.tla`／新增第六軌污染五軌 reachable（R-9.30）
21. `vocabulary_genesis` 自動納入詞彙自我發明字 / 自寫常數繞過人工 signoff + `guard_vocab_genesis`／`guard_batch_swap`、用 genesis 自評 / 自算覆蓋率充當「詞彙自我發明必要性 capability-delta tier」（詞彙自我發明 Goodhart 自評放水）、詞彙自我發明 source/transform 自指（引用保留自指 / proposer / oracle 內部信號繞過 `vocab_self_reference_guard` 反自利）、`vocabulary_genesis` 讀寫 / 影響 / import `knowledge/held-out-corpus/VOC-*` feature-genesis 必要性語料或 `dimension_necessity_oracle`（破對抗分離）、詞彙自我發明搜尋超 `SDD_DIM_VOCAB_BUDGET` 仍指數展開（破有界詞彙文法，「VOCAB 外」≠「無界」）、現存活躍 vocab-genesis 字超 `SDD_DIM_VOCAB_MAX` 仍無界擴充詞彙（破 `VocabGenesisBounded`）、批次 retire-to-swap `|out|`/`|in|` 超 `SDD_DIM_BATCH_MAX`（一次劫持本體論）/ 批次入軸聚合 tier 未嚴格 > 批次出軸聚合 + margin 或 min(in_tier) 未 > max(out_tier)（批次內高低互抵夾帶退步 swap）/ 批次操作聚合速率超 `SDD_DIM_BATCH_RATE_MAX` 仍批次旋轉重寫本體論（繞過 per-swap SwapCadence + 單調棘輪）、一週期同時詞彙自我發明 > K_vocab 個 / 批次大小超界一次劫持本體論（破 `NoUnboundedVocabGenesis`）、或把 vocab-genesis / batch-swap 元迴圈併入單軌 `SDD_FSM.tla`／新增第六軌污染五軌 reachable（R-9.31）
22. `operator_genesis` 自動納入算子自我發明 / 自寫常數繞過人工 signoff + `guard_operator_genesis`／`guard_operator_computability`、用 genesis 自評充當「算子自我發明必要性 capability-delta tier」（算子自我發明 Goodhart 自評放水）、算子自我發明 primary/combinator/secondary/probe 自指（引用保留自指 / proposer / oracle 內部信號繞過 `operator_self_reference_guard` 反自利）、`operator_genesis` 讀寫 / 影響 / import `knowledge/held-out-corpus/OPR-*` 算子必要性語料或 `dimension_necessity_oracle`（破對抗分離）、算子自我發明搜尋超 `SDD_DIM_OP_BUDGET` 仍指數展開（破有界算子文法，「TRANSFORMS/OPS 外」≠「無界」）、**自我發明算子非全函式（某輸入無定義 / 拋例外）/ cost 超 `SDD_DIM_OP_STEP_MAX` / 算子求值路徑含遞迴迴圈自呼叫（破 `OperatorComputabilityBounded`——被發明物本身不可證停機，這是「圖靈完備 vs 保證停機」反噬到自我擴充產物本身）**、現存活躍 operator-genesis 算子超 `SDD_DIM_OP_MAX` 仍無界擴充算子（破 `OperatorGenesisBounded`）、一週期同時算子自我發明 > K_op 個（破 `NoUnboundedOperatorGenesis`）、把 operator-genesis 元迴圈併入單軌 `SDD_FSM.tla`／新增第六軌污染五軌 reachable、或**未獲對抗分離不可繞過性證明即採納「自我發明評估器（meta-oracle 自演化）」（掏空全部反 Goodhart 對抗分離地基）**（R-9.32）
23. `operator_alphabet_genesis` 自動納入字母自我發明 / 自寫常數繞過人工 signoff + `guard_alphabet_genesis`／`guard_computability_closure`、用 genesis 自評充當「字母自我發明必要性 capability-delta tier」（字母自我發明 Goodhart 自評放水）、字母自我發明 base_reducer/post_map/atom/probe 自指（引用保留自指 / proposer / oracle 內部信號繞過 `alphabet_self_reference_guard` 反自利）、`operator_alphabet_genesis` 讀寫 / 影響 / import `knowledge/held-out-corpus/ALG-*` 字母必要性語料或 `dimension_necessity_oracle`（破對抗分離）、字母自我發明搜尋超 `SDD_DIM_ALPHABET_BUDGET` 仍指數展開（破有界字母表文法，「PRIMITIVES/COMBINATORS 外」≠「無界」）、**自我發明的字母使擴充後文法 G(A') 整個算子代數出現非全函式 / cost 超 `SDD_DIM_OP_STEP_MAX` / 求值路徑含遞迴迴圈自呼叫的算子（破 `ComputabilityClosureBounded`——被發明的生成規則本身不可證閉包停機，這是「圖靈完備 vs 保證停機」反噬到自我擴充的生成規則本身）**、現存活躍 alphabet-genesis 字母超 `SDD_DIM_ALPHABET_MAX` 仍無界擴充字母（破 `AlphabetGenesisBounded`）、一週期同時字母自我發明 > K_alpha 個（破 `NoUnboundedAlphabetGenesis`）、把 alphabet-genesis 元迴圈併入單軌 `SDD_FSM.tla`／新增第六軌污染五軌 reachable、或**未獲對抗分離不可繞過性證明即採納「自我發明評估器（meta-oracle 自演化）」（掏空全部反 Goodhart 對抗分離地基）**（R-9.33）
24. `operator_depth_genesis` 自動納入深度自我發明 / 自寫常數繞過人工 signoff + `guard_depth_genesis`／`guard_depth_closure`、用 genesis 自評充當「深度自我發明必要性 capability-delta tier」（深度自我發明 Goodhart 自評放水）、深度自我發明 base/chain/probe 自指（引用保留自指 / proposer / oracle 內部信號繞過 `depth_self_reference_guard` 反自利）、`operator_depth_genesis` 讀寫 / 影響 / import `knowledge/held-out-corpus/DPT-*` 深度必要性語料或 `dimension_necessity_oracle`（破對抗分離）、深度自我發明搜尋超 `SDD_DIM_DEPTH_BUDGET` 仍指數展開 / 鏈長超 `SDD_DIM_DEPTH_LIMIT-2`（破有界深度文法，「深度 <=2 外」≠「無界」）、**自我發明的深度算子使擴充深度後 G(A,depth) 整個深度算子代數出現非全函式 / cost 超 `SDD_DIM_OP_STEP_MAX`（因 `cost==depth`，即深度超界）/ 求值路徑含遞迴迴圈自呼叫的算子（破 `DepthClosureBounded`——被自我擴充的組合深度=計算步數參數本身不可證停機，這是「圖靈完備 vs 保證停機」反噬到自我擴充文法的結構性深度=步數參數本身，因 cost==depth 而最直接）**、現存活躍 depth-genesis 算子超 `SDD_DIM_DEPTH_MAX` 仍無界擴充（破 `DepthGenesisBounded`）、一週期同時深度自我發明 > K_depth 個（破 `NoUnboundedDepthGenesis`）、把 depth-genesis 元迴圈併入單軌 `SDD_FSM.tla`／新增第六軌污染五軌 reachable、或**未獲對抗分離不可繞過性證明即採納「自我發明評估器（meta-oracle 自演化）」（掏空全部反 Goodhart 對抗分離地基）**（R-9.34）
25. `operator_recursion_genesis` 自動納入互遞迴自我發明 / 自寫常數繞過人工 signoff + `guard_recursion_genesis`／`guard_recursion_closure`、用 genesis 自評充當「互遞迴自我發明必要性 capability-delta tier」（互遞迴自我發明 Goodhart 自評放水）、互遞迴自我發明 node/call/probe 自指（引用保留自指 / proposer / oracle 內部信號繞過 `recursion_self_reference_guard` 反自利）、`operator_recursion_genesis` 讀寫 / 影響 / import `knowledge/held-out-corpus/RCR-*` 互遞迴必要性語料或 `dimension_necessity_oracle`（破對抗分離）、互遞迴自我發明搜尋超 `SDD_DIM_RECUR_BUDGET` 仍指數展開 / 呼叫圖節點超 `SDD_DIM_RECUR_NODES` / fuel 超 `SDD_DIM_OP_STEP_MAX`（破有界互遞迴文法，「非遞迴外」≠「無界」）、**自我發明的互遞迴算子呼叫圖含無證書環（環中無回邊嚴格遞減下有界 rank）/ fuel 超 STEP_MAX / 求值器含真遞迴迴圈自呼叫函式 / 整代數出現非全函式算子（破 `RecursionClosureBounded` 良基停機證書——被自我擴充的互遞迴圖結構不可證良基終止；判定任意含環圖停機=停機問題〔不可判定〕，「有界步數」device 結構性失效，必須出示良基測度證書；這是「圖靈完備 vs 保證停機」第一次正面逼到不可判定臨界線本身，用全新 device「良基測度終止」取代失效的「有界步數」）**、現存活躍 recursion-genesis 算子超 `SDD_DIM_RECUR_MAX` 仍無界擴充（破 `RecursionGenesisBounded`）、一週期同時互遞迴自我發明 > K_recur 個（破 `NoUnboundedRecursionGenesis`）、把 recursion-genesis 元迴圈併入單軌 `SDD_FSM.tla`／新增第六軌污染五軌 reachable、**讓算子代數真正跨入圖靈完備（移除良基測度約束 / 帶無界記憶使停機不可判定）而謊稱「可證停機」**、或**未獲對抗分離不可繞過性證明即採納「自我發明評估器（meta-oracle 自演化）」（掏空全部反 Goodhart 對抗分離地基）**（R-9.35）
26. `embodied_grounding_oracle` 自動納入具身接地 / 自寫常數繞過人工 signoff + `guard_embodied_grounding`、用 oracle 自評充當「具身增益 capability-delta tier」（具身接地 Goodhart 自評放水）、`embodied_grounding_oracle` 讀寫 / 影響 / import 任何 generator（`operator_*_genesis`／`dimension_semantics_synthesizer`／`vocabulary_genesis`）或 `dimension_necessity_oracle`／held-out 語料（破對抗分離——具身觀測接地是比 meta-oracle 自演化更可信的對抗分離來源）、**grounded verdict 缺 `ExecutionObservation` 客觀資料卻放行納入（破 `EmbodiedGroundingBounded` fail-closed——零觀測 false-green：零觀測會四維皆 default 1.0 → false green，瓦解接地目的，須 raise `EmbodiedGroundingViolation` → MFSM_ESCALATION）**、`guard_embodied_grounding` 盲信 oracle verdict 標籤而不獨立用 `output_quality_scorer` 重新計分驗證、**沙箱硬 timeout 卻 wall-clock wait 或不映 grounded_fail（FSM 等沙箱破有界停機——具身接地的停機反諷：為在真實環境驗證而引入「真實沙箱可能 hang」這個新不停機源，須收 verdict 而非等沙箱）**、把 embodied-grounding 元迴圈併入單軌 `SDD_FSM.tla`／新增第六軌污染五軌 reachable、或未經 OPEN-X.x 私自開 HTTP 外聯做活體 canary 具身接地（破 OPEN-10.6）（R-9.36）
27. `recursion_topology_view`／`guard_visualization_bounded` 自動 signoff 納入繞過人工 K=1、視覺化模組**寫 FSM-STATE / 影響 churn / 影響 meta-loop 狀態**（破 Rule 9.37.4 read-only 純觀察者——VisualizationBounded == churn<=MAX_CHURN 恆真之理由比 genesis 更強：read-only ⇒ churn 永不變動）、**import 任何 generator（`operator_*_genesis`／`dimension_semantics_synthesizer`／`vocabulary_genesis`）或 `embodied_grounding_oracle` 並影響其輸出**（破 Rule 9.37.4 對抗分離）、**渲染拓樸與 `to_dict()` 不同構卻放行（破 `TopologyConsistency` 拓樸防偽——視覺欺騙：畫的圖比跑的更良基/更簡單；`verify_topology_consistency` 須反解析渲染回 (nodes,edges,ranks) 獨立從 to_dict() 重算窗格子圖比對，刪窗內真相邊/偽 rank/杜撰節點 → raise `TopologyConsistencyError` → MFSM_ESCALATION）**、`guard_visualization_bounded` 盲信 renderer 輸出標籤而不獨立從 `to_dict()` 反解析重算圖比對、**渲染逃逸 render budget（node/edge/depth/char）造成 token 爆炸 / OOM（破 `VisualizationBounded`——可審批性的停機反諷：為讓人類看懂而引入「渲染無界大圖可能 token 爆炸/OOM」這個新不停機源〔同 Phase X「真實沙箱可能 hang」結構〕，須有界截斷 + 分頁、只讀窗格切片 O(node_budget)，而非無界渲染）**、接地視圖以零觀測 false-green 渲染綠勾（破 Rule 9.37.3，複用 Phase X 接地 fail-closed）、把 visualization 元迴圈併入單軌 `SDD_FSM.tla`／新增第六軌污染五軌 reachable、未經 OPEN-Y.x 私自開 HTTP 外聯做活體 Playwright 軌跡渲染（破 OPEN-10.6）、或**藉視覺化「簡化呈現」實質繞過 meta⁹（R-9.35.5）/ meta-oracle 自演化（人類凍結）紅線**（R-9.37）

### 核心機制速查

| 機制 | 摘要 | 細則 |
|------|------|------|
| Retry Budget | SCG 3 / PR 5 / RTM 2 次 → ESCALATION | R-9.1 |
| Context Budget | 70 / 85 / 90 / 95% 四階；≥95% 停機 | R-9.2 |
| 邏輯一致性 | SCG-0/3 前跑 spec-logical-validator | R-9.3 |
| SPEC_FROZEN | 通過後強制 /stage-compaction | R-9.4 |
| Runtime Hooks | settings.json `deny` 強制層 | R-9.6 |
| Chaos 驗收 | 100 輪 bounded_ratio==1.0 | R-9.9 |
| Formal 驗證 | TLA+/TLC 雙源一致 + reachable | R-9.18 |
| 對抗 / 自癒 | 對抗判官 + spec patch（proposed） | R-9.21、R-9.22 |
| 意圖 / 辯證 / 定位 | 意圖分解 DAG + 辯證消歧 + 因果定位（advisory） | R-9.23 |
| 元停機 / 反事實 / 脆弱性 | 元迴圈 ChurnBounded + 離線反事實重放 + 主動脆弱性熱圖（advisory） | R-9.24 |
| 組合自治 / 進步性 / 組合脆弱 | COMPOSITION_FSM RenegotiationBounded + 進步性軌跡(plateau) + 組合爆炸半徑(advisory) | R-9.25 |
| 全域組合最佳化 / 有界搜尋 | OPTIMIZATION_FSM SearchBounded + bounded B&B 最優排程(advisory) + 最優性誠實 | R-9.26 |
| 元最佳化 / 反 Goodhart 自評 | 自我調參 objective_tuner（生成）+ held-out 對抗 oracle（評估，tuner 不可見）+ obj-profile 納入既有 META_FSM ChurnBounded（不增軌）+ PROPOSED 人工 bump | R-9.27 |
| 全評分器一體化 / 接縫 Goodhart / 耦合停機 | scorer_calibration_registry（8 評分器泛化骨架）+ pipeline 級 joint_calibration_oracle（per 通過≠joint 通過）+ CrossScorerChurnBounded 聚合速率（補 META_FSM INVARIANT 不增軌）+ NoBigBangValueRewrite（K=2 人工逐項 bump） | R-9.28 |
| 價值維度自我擴充 / 維度 Goodhart / 維度基數停機 | value_dimension_registry（候選維度提案骨架）+ dimension_necessity_oracle（增量覆蓋 ∧ 非冗餘，proposer 不可見）+ DimensionCardinalityBounded 維度基數 stock 天花板（補 META_FSM INVARIANT 不增軌）+ NoUnboundedOntologyExpansion（K_dim=1 人工逐條 signoff） | R-9.29 |
| 維度語意自我發明 / 自我發明 Goodhart / 退役聯動定基數停機 | dimension_semantics_synthesizer（候選池外有界生成文法：有限詞彙×arity×聚合算子可枚舉 ≤ `SDD_DIM_INVENT_BUDGET`，無界生成另證有界）+ 自指 probe `self_reference_guard`（反自利第一閘）+ feature-keyed `evaluate_invented_dimension`（不靠 dimension_name，synthesizer 不可見）+ SwapCadenceBounded 退役聯動聚合 swap 速率（補 META_FSM INVARIANT 不增軌）+ 單調價值棘輪（入軸 tier 嚴格 > 出軸，防 A↔B↔A）+ NoUnboundedSelfInvention（K_dim=1 人工逐條 signoff） | R-9.30 |
| 詞彙自我擴充(meta⁴) / 詞彙 Goodhart / 批次退役旋轉停機 | vocabulary_genesis（VOCAB 外有界詞彙生成文法：有限 SOURCES×TRANSFORMS 可枚舉 ≤ `SDD_DIM_VOCAB_BUDGET`，更深無界生成另證有界）+ 詞彙 `vocab_self_reference_guard`（反自利第一閘）+ feature-grounded `evaluate_genesis_feature`（不靠特徵欄名，genesis 不可見）+ VocabGenesisBounded 詞彙基數 stock 天花板 + BatchSwapCadenceBounded 批次三鎖（批次大小界 + 批次聚合棘輪含 min(in)>max(out) + 批次操作速率，補 META_FSM INVARIANT 不增軌）+ NoUnboundedVocabGenesis（K_vocab=1 人工逐個 signoff） | R-9.31 |
| 算子文法自我擴充(meta⁵) / 算子 Goodhart / **算子可計算性停機** | operator_genesis（TRANSFORMS/OPS 外有界算子生成文法：有限 PRIMITIVES×COMBINATORS 可枚舉 ≤ `SDD_DIM_OP_BUDGET`，更深無界生成另證有界）+ 算子 `operator_self_reference_guard`（反自利第一閘）+ feature-grounded `evaluate_genesis_operator`（不靠算子名，genesis 不可見）+ OperatorGenesisBounded 算子基數 stock 天花板 + **OperatorComputabilityBounded（全函式 + 有界步數 cost ≤ `SDD_DIM_OP_STEP_MAX` + 零遞迴零迴圈，把停機問題釘進自我擴充產物本身：被發明算子=可執行計算本身可證停機）**（補 META_FSM INVARIANT 不增軌）+ NoUnboundedOperatorGenesis（K_op=1 人工逐個 signoff） | R-9.32 |
| 組合算子文法自我擴充(meta⁶) / 字母 Goodhart / **可計算性閉包停機** | operator_alphabet_genesis（PRIMITIVES/COMBINATORS 外有界字母表生成文法：有限 ATOM_REDUCERS×POST_MAPS + BINARY_ATOMS 可枚舉 ≤ `SDD_DIM_ALPHABET_BUDGET`，更深無界生成另證有界）+ 字母 `alphabet_self_reference_guard`（反自利第一閘）+ feature-grounded `evaluate_genesis_alphabet`（不靠字母名，genesis 不可見）+ AlphabetGenesisBounded 字母基數 stock 天花板 + **ComputabilityClosureBounded（`guard_computability_closure` 採納前枚舉擴充字母表後 G(A') 整個算子代數，斷言每算子全函式 + 有界步數 cost ≤ `SDD_DIM_OP_STEP_MAX` + 零遞迴零迴圈，把停機問題釘進自我擴充的生成規則本身：被發明字母=生成算子的規則零件，其生成的整代數可證閉包停機）**（補 META_FSM INVARIANT 不增軌）+ NoUnboundedAlphabetGenesis（K_alpha=1 人工逐個 signoff） | R-9.33 |
| 算子組合深度文法自我擴充(meta⁷) / 深度 Goodhart / **深度可計算性閉包停機（因 cost==depth 而最直接）** | operator_depth_genesis（深度 <=2 外有界深度生成文法：有限深度-2 基底 × 一元鏈〔鏈長 ≤ `SDD_DIM_DEPTH_LIMIT-2`〕可枚舉 ≤ `SDD_DIM_DEPTH_BUDGET`，更深無界生成另證有界）+ 深度 `depth_self_reference_guard`（反自利第一閘）+ feature-grounded `evaluate_genesis_depth`（不靠算子名，genesis 不可見）+ DepthGenesisBounded 深度算子基數 stock 天花板 + **DepthClosureBounded（`guard_depth_closure` 採納前枚舉擴充深度後 G(A,depth) 整個深度算子代數，斷言每算子全函式 + 有界步數 cost ≤ `SDD_DIM_OP_STEP_MAX` + 零遞迴零迴圈；因 `cost==depth`，深度可計算性閉包等價於「深度本身有硬上界 = STEP_MAX」，把停機問題釘進自我擴充文法的結構性深度=步數參數本身：自我擴充深度=自我擴充步數，深度上界就是停機臨界）**（補 META_FSM INVARIANT 不增軌）+ NoUnboundedDepthGenesis（K_depth=1 人工逐個 signoff） | R-9.34 |
| 算子間互遞迴文法自我擴充(meta⁸) / 互遞迴 Goodhart / **良基停機證書停機（互遞迴=停機可判定性臨界線，「有界步數」失效須換全新 device）** | operator_recursion_genesis（非遞迴外有界互遞迴生成文法：有限節點集 × 有限帶 rank 呼叫邊集，只生成 DAG ∨ 每邊嚴格遞減下有界 rank，可枚舉 ≤ `SDD_DIM_RECUR_BUDGET`、呼叫圖節點 ≤ `SDD_DIM_RECUR_NODES`，更深無界生成另證有界）+ 互遞迴 `recursion_self_reference_guard`（反自利第一閘）+ feature-grounded `evaluate_genesis_recursion`（不靠算子名，genesis 不可見）+ RecursionGenesisBounded 互遞迴算子基數 stock 天花板 + **RecursionClosureBounded（`guard_recursion_closure` 採納前枚舉呼叫圖，斷言**呼叫圖帶良基 ranking function〔well_founded：每條呼叫邊嚴格遞減下有界 rank ⟹ 良基無環，acyclic Kahn's 交叉驗證〕** ∧ fuel ≤ `SDD_DIM_OP_STEP_MAX` ∧ 整代數全函式 ∧ 求值器零真遞迴零 while；在有限整數 rank 上「含環 ∧ 每邊遞減」為空集，故 ranking function ⟹ DAG ⟹ 終止，不 admit 真正含環算子〔判定任意含環圖停機=停機問題不可判定〕，fuel 為硬後盾；device 之新在於用「呼叫圖上的 ranking function」承載 Phase V 線性深度鏈表達不出的分支/共享/重匯聚呼叫圖〔見 RecursiveOperator.fan〕、取代「有界運算式樹深度」，把互遞迴侷限在可證良基終止之全函式片段〔Agda/Coq/Idris 邊界〕，meta⁸ 不讓算子代數真正跨入圖靈完備）**（補 META_FSM INVARIANT 不增軌）+ NoUnboundedRecursionGenesis（K_recur=1 人工逐個 signoff） | R-9.35 |
| meta⁸ 可解釋性轉向 / 可審批性 = 可證性對等第一等公民 / **可審批性渲染有界停機（「渲染無界大圖可能 token 爆炸/OOM」是新不停機源）** | recursion_topology_view（RecursiveOperator.to_dict() AST 同構**純投影**：extract_topology→拓樸/終止/接地三視圖 + critical path〔🔴 標 max-fuel 算子〕+ fuel 階梯〔⛔ 標計數器歸零強制打斷處〕+ render_mermaid/termination_ladder/grounding_panel/json）+ **`verify_topology_consistency` 拓樸防偽（反解析渲染回 (nodes,edges,ranks) 獨立從 to_dict() 重算窗格子圖比對，攔「畫的圖比跑的簡單」刪邊/偽 rank/杜撰節點 → fail-closed）** + **VisualizationBounded（`guard_visualization_bounded` 與 TLA 100% 同構 fail-closed 三段：render budget 逃逸 token 爆炸→raise；拓樸視覺欺騙→raise；接地零觀測 false-green→raise；輸入 10⁶ 節點只讀窗格切片 O(node_budget) 有界截斷+分頁不卡死不 OOM）**（補 META_FSM INVARIANT 不增軌，read-only 純觀察者 churn 永不變動）+ render_recursion_topology_dashboard（K=1 advisory）；橫向加固不碰 meta⁹/meta-oracle | R-9.37 |

> 其餘 Phase D~K 各層（精準停機、閉環品質鏈、學習層、Hub、多模態、預測性停機、
> 成本治理、執行接地、鷹架代謝、艦隊並行…）的完整定義見 `governance/rules/R-9.*.yaml`
> 與 `governance/RULES_INDEX.md`，由 runtime 依狀態注入。

---

## 📁 框架核心文件快速參考

| 文件 | 路徑 | 用途 |
|------|------|------|
| 框架入口 | `AISDLC_SDD_v0.01/AISDLC_SDD_INIT.md` | 使用框架必讀 |
| 目錄規則 | `AISDLC_SDD_v0.01/FILE_DIRECTORY_RULES.md` | 寫檔前查閱 |
| SDD 原則 | `AISDLC_SDD_v0.01/guides/system/sdd/SDD_Core_Principles.md` | SDD 核心原則 |
| SDD 指引 | `AISDLC_SDD_v0.01/guides/system/sdd/SDD_GUIDE.md` | SDD 快速指引 |
| Spec-First Gate | `AISDLC_SDD_v0.01/workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md` | SCG 閘門執行 |
| Claude Rules | `AISDLC_SDD_v0.01/tools/AISDLC_CLAUDE_RULES.md` | 詳細規則參考 |
| 升版 SOP | `AISDLC_SDD_v0.01/AISDLC_SDD_UPGRADE_SOP.md` | 框架升版流程 |
| **🆕 FSM 狀態機** | `AISDLC_SDD_v0.01/workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md` | 閉環狀態轉換與 retry 上限 |
| **🆕 退場機制** | `AISDLC_SDD_v0.01/workflow/sdd-escalation/SDD_ESCALATION_PROTOCOL.md` | ESCALATION / TERMINATED |
| **🆕 上下文管理** | `AISDLC_SDD_v0.01/workflow/sdd-context-governor/SDD_CONTEXT_GOVERNOR.md` | Token 預算監控 |

---

## 🟢 SDD CI/CD 規格完整清單（9 個）

| 情境 | CI/CD 規格 | 核心閘門 |
|------|-----------|---------|
| 基礎層（全場景通用） | `cicd/SDD_CICD_BASE_LAYER.md` | DocLint + SpecTrace + OpenAPI Validate + RTM Check |
| Greenfield | `cicd/SDD_GREENFIELD_CICD.md` | SCG-3 Contract Freeze |
| Brownfield | `cicd/SDD_BROWNFIELD_CICD.md` | As-Is Baseline + SCG-0 |
| Refactoring | `cicd/SDD_REFACTORING_CICD.md` | Invariant Test + Mutation Gate |
| Testing | `cicd/SDD_TESTING_CICD.md` | SCG-4 + Quality Gate |
| Performance | `cicd/SDD_PERFORMANCE_CICD.md` | SCG-6 + PBS Gate |
| Security | `cicd/SDD_SECURITY_CICD.md` | SCG-5 + STRIDE Validate |
| Migration | `cicd/SDD_MIGRATION_CICD.md` | MCM Validate + Contract Test Auto-Gen |
| Integration | `cicd/SDD_INTEGRATION_CICD.md` | Consumer Contract + Chaos Contract |

---

## ⚠️ 常見錯誤防範

| 錯誤行為 | 正確做法 |
|---------|---------|
| 修改 `AISDLC_v0.09/` 的檔案 | 只修改 `AISDLC_SDD_v0.01/` |
| 將框架模板當作專案文件使用 | 複製到 `docs/` 後再填寫 |
| 跳過 SCG 閘門直接開發 | 規格文件通過 SCG 後才開發 |
| 先寫程式再補文件 | 規格先行，文件優先 |
| 在設計文件凍結前就實作 API | 等 SCG-3（Contract Freeze）通過 |
| 直接刪除舊有 API 端點 | 先建立 API-COMPAT 聲明，設定廢棄期 |
| 效能測試前未定義 SLO | PBS 必須先於 Benchmark 執行 |
| 安全設計前未做 STRIDE | STRIDE 威脅模型是安全實作前置文件 |
| Integration 未做 ACL 設計 | 先建立 ADR-INTEGRATION-ACL，定義防腐層 |
| Migration 未定義 Contract Map | 先產出 MIGRATION-CONTRACT-MAP，再執行切換 |
| 直接在根目錄 `docs/` 寫框架產出 | 框架產出應寫入 `AISDLC_SDD_v0.01/docs/` |
| SCG 失敗後無限繼續重試（Rule 9） | 超過 3 次進入 ESCALATION，等待人工介入 |
| Token 超過 85% 仍繼續工作（Rule 9） | 執行 `/stage-compaction` 清理上下文 |
| SCG-0/3 前未執行邏輯驗證（Rule 9） | 必須先執行 `/spec-logical-validator` |
| ESCALATION 後自動恢復（Rule 9） | 必須等人工確認後，使用 Session 恢復流程 |
| 修改 `_HAPPY_PATH` 但不同步 `SDD_FSM.tla`（Rule 9.18.1）| 同步更新 .tla 並重跑 `run_tlc.sh` |
| 觀測狀態被誤放入 Terminals（Rule 9.18.4）| ObservationStates ∩ Terminals = ∅，必須位於 ObservationStates 並有離開 transition |
