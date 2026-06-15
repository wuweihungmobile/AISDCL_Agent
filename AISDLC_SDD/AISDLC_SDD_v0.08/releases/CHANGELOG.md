# AISDLC-SDD Framework CHANGELOG

**維護者**: AISDLC-SDD Framework Team
**最後更新**: 2026-06-16

---

## [v0.08] - 2026-06-16（Copy-on-Evolve 自 v0.07；v0.07 凍結唯讀）

### 新增（B 軌「鷹架代謝」L4→L5 信號 — GC 自動提議退役接入 FSM 主迴圈；AutoSDD_improving_17 W-17-1/W-17-2）
- `tools/fsm_runtime/fsm_runtime.py` — 把既有 `scaffold_gc.run_gc()`（產 `RetirementProposal` proposed 退役提議，原測試-only / 手動）**接入主迴圈**：新增 `_SCAFFOLD_GC_AUTO_PROPOSE_ENV` 開關 + `_scaffold_gc_auto_propose_enabled()` + `scaffold_gc_stats()`（L5 可量測信號 + XAI 安全證書）；`enter_scaffold_gc()` 進態 SCAFFOLD_GC 後 flag-gated 自動跑 `run_gc` 算 ROI 落 `SCAFFOLD-ROI-{date}.md` + 填 `scaffold_gc_tracking`。**預設 OFF＝v0.07 行為（零退化）**；fail-closed：run_gc 任何失敗進態仍成功、不偽造報告。行使 arch_fitness FF-16 GAP-X2「代謝肌肉從未收縮」之 Rule 9.20.5。
- `tools/fsm_runtime/tests/test_scaffold_gc_auto_propose_wiring.py` — 9 新測試（flag off 零退化 ×2 / flag on 自走 run_gc+tracking / 報告真實落盤 / run_gc 失敗 fail-closed / GC 零 set_maturity 呼叫〔R-9.20 #11〕/ 非 RELEASE 源仍 raise / 零提議度量穩健 / roi_ladder 升冪+by_transition）。

### 紅線守界（B 軌）
- `run_gc` 只產退役提議、**永不自動退役 active 規則**；退役維持 🔴 人工 `rule_loader.set_maturity(reviewed_by=...)`（R-9.20 絕對禁令 #11 不弱化）＝rubric「L5 在環上守界」之守界；`scaffold_gc_stats` 純讀不碰 meta-oracle（GC 是 ROI 統計層非生成器）。**無 FSM 狀態/規則/`*.tla` 變更**（diff v0.07 逐位元零差異 → 免五軌 TLC）。

---

## [v0.07] - 2026-06-15（Copy-on-Evolve 自 v0.06；v0.06 凍結唯讀）

### 新增（B 軌「規則自演化」L4→L5 信號 — SLV 自動提議接入 FSM 主迴圈；AutoSDD_improving_16 W-16-1/W-16-2）
- `tools/fsm_runtime/fsm_runtime.py` — 把既有 `slv_generator.propose_slv_from_fpl()`（`trust_level:proposed` 草案合成，原 proposal-only / 手動 CLI）**接入主迴圈**：新增 `_SLV_AUTO_PROPOSE_ENV` 開關 + `_slv_auto_propose_enabled()` + staticmethod `_auto_draft_slv(fpl_id)`（純合成 fail-closed）+ `learning_loop_stats()`（L5 可量測信號 + XAI 良基終止證書）；`exit_production_behavioral_signal()` 加 optional `fpl_id`，**learn 分支**轉態到 LEARNING_COMMIT 後 flag-gated 自動 draft proposed 草案 + 填 `learning_commit_tracking`。**預設 OFF＝v0.06 行為（零退化）**；附帶修 **DEF-16-001**（learn 採納鏈結構性斷裂）。
- `tools/fsm_runtime/tests/test_slv_auto_propose_wiring.py` — 9 新測試（flag off 零退化 ×2 / flag on 自走 draft+tracking / learn→人 verify→approve 鏈閉合 / 未 verify approve→raise〔R-9.11〕/ FPL 不存在 fail-closed / 合成失敗 fail-closed / 零事件度量穩健 / 計數+churn_max 一致）。

### 紅線守界（B 軌）
- 草案恆 `trust_level:proposed`（R-9.11，永不自動升 verified）；`trust_level→verified` 維持 🔴 人工（`exit_learning_commit` verified 強制檢查不動）＝rubric「L5 在環上守界」之守界；採納經 `meta_halt_monitor` ChurnBounded/GraduationRatchet（R-9.24 不弱化）；`learning_loop_stats` 純讀不碰 meta-oracle（R-9.37）。

### 不變
- **無 FSM 狀態/規則變更**：`LEARNING_COMMIT` 既有 state、`PRODUCTION_BEHAVIORAL_SIGNAL→LEARNING_COMMIT`（learn）既有邊，`transition_rules.py` + 全 5 `*.tla` 對 v0.06 **逐位元零差異**（diff 實測全 ZERO DIFF），Rule 9.18.1 不啟動、五軌 TLC 既有證明維持有效；ID_REGISTRY 不取新 ACT/rule。

### 驗證
- v0.07 `pytest -m "not chaos"` = 1517 passed / 4 skipped（v0.06 1508 + 9，只增不減）；新 wiring 9 passed；flag OFF 既有 37 相關 passed 零退化；雙軌 ci-gate exit 0「v0.01 凍結基線 + v0.07 最新演化版」（FF-17 自證入閘）。

---

## [v0.06] - 2026-06-15（Copy-on-Evolve 自 v0.05；v0.05 凍結唯讀）

### 新增（B 軌「流程自治」L3→L4 升級 — auto_recovery 接入 FSM 主迴圈；AutoSDD_improving_15 W-15-1）
- `tools/fsm_runtime/fsm_runtime.py` — 把既有 `auto_recovery.py`（Rule 9.14 有界 1-shot 自癒，原 proposal-only / 需 orchestrator 手動觸發）**接入主迴圈**：新增 `_AUTO_RECOVERY_ENV` 開關常數 + `_auto_recovery_enabled()` + `_gate_is_resumable()` 預檢 + `auto_recovery_stats()`（L4 可量測信號）；`record_gate_result()` escalate 分支 **flag-gated 自動嘗試** `enter_auto_recovery`，把既有 `ESCALATION→AUTO_RECOVERY_ATTEMPT` 邊（TLA `T_EnterAutoRecover` 已模型化）由手動改自動觸發。**預設 OFF＝v0.05 行為（零退化）**；fail-closed（structural/bounds→ESCALATION_FINAL、例外停 ESCALATION）。
- `tools/fsm_runtime/tests/test_auto_recovery_wiring.py` — 9 新測試（flag off 零退化 / flag on 自走進 recovery / 完整閉環 success 回 gate / structural→FINAL / bounds→FINAL / fail→FINAL / resumable 預檢 / 空 session 零率）。

### 不變
- **無 FSM 狀態/規則變更**：`AUTO_RECOVERY_ATTEMPT` 為既有合法 state、`ESCALATION→AUTO_RECOVERY_ATTEMPT` 為既有合法邊，`_HAPPY_PATH` 與全部 `*.tla` 零改動（僅改 Python 觸發者、非狀態宇宙），Rule 9.18.1 不啟動、五軌 TLC 既有證明維持有效；ID_REGISTRY 維持 act=173 / rule="9.39"（接線既有能力，不取新 ACT/rule）。

### 驗證
- v0.06 `pytest -m "not chaos"` = 1508 passed / 4 skipped（v0.05 1499 + 9，只增不減）；flag OFF 既有 86 passed 零退化；雙軌 ci-gate exit 0「v0.01 凍結基線 + v0.06 最新演化版」（FF-17 自證 v0.06 自動入閘）。

### 共享 infra 同輪修（DEF-15-001，免 Copy-on-Evolve）
- `scripts/copy_on_evolve.sh` — 修 `tar --exclude build/reports` 誤殺 FSM 種子模板 `build/reports/fsm/FSM-STATE-TEMPLATE.yaml`（state_loader 必需真輸入）：排除後補回該模板；`scripts/tests/test_copy_on_evolve.py` 加回歸鎖 case。首次真實 v0.06 演化當場揭露（46+ FSM 測試全紅）。

---

## [v0.05] - 2026-06-15（Copy-on-Evolve 自 v0.04；v0.04 凍結唯讀）

### 新增（DEF-10-002b 回流 — Copy-on-Evolve 演化版必納官方閘門固化；AutoSDD_improving_11 W-11-2）
- `tools/arch_fitness/arch_fitness.py` — 新增 **FF-17「Copy-on-Evolve 演化版必納官方閘門」** 結構守門：把 improving_04 對 DEF-03-001 的雙軌**點修**固化為**結構不變量**。新增常數 `CI_GATE_PATH`、純函式 `_latest_version_dir()`、`check_ff17_evolution_version_gate_coverage()`（靜態讀 `scripts/ci-gate.sh`，斷言四錨點動態最新版偵測；退回靜態寫死＝`structural fail`），註冊進 `ALL_CHECKS`；docstring 16→17、exit-code 清單補 FF-17。與 FF-14 同源（靜態讀 CI 腳本、純讀、跨平台不執行 shell）。
- `tools/fsm_runtime/tests/test_arch_fitness.py` — 5 新測試（真 repo 涵蓋最新版 / 合成雙軌 PASS / 寫死單版 fail / 漏 append-latest fail / 腳本缺 INFO 略過）。
- **設計決策**：不另開 R-9.x 規則（會連鎖 FF-8/10/12 且屬自演化 meta-loop 異類關注點）；arch_fitness 本即治理層 fitness-function 套件，FF-17 即最小正確固化（Rule 2/3）。

### 不變
- **無 FSM 狀態/規則變更**（`_HAPPY_PATH` 與 `*.tla` 零改動，Rule 9.18.1 不啟動）；ID_REGISTRY 維持 next_free act=173 / rule="9.39"（純 fitness-function 新增，不取新 ACT/rule）。

### 驗證
- v0.05 `pytest -m "not chaos"` = 1499 passed / 4 skipped（v0.04 1494 + 5，只增不減）；arch_fitness 87 passed；雙軌 ci-gate exit 0「v0.01:1478 v0.05:1499」——v0.05 作為最新演化版自動納入官方閘門，自證 FF-17 不變量。

---

## [v0.04] - 2026-06-14（Copy-on-Evolve 自 v0.03；v0.03 凍結唯讀）

### 修正（DEF-02-002 回流 — tlc_runner 計數標籤接反；AutoSDD_improving_03 W2）
- `tools/fsm_runtime/tlc_runner.py` — 抽出 module-level `parse_tlc_summary(out)`：以 **last-match**（`re.findall[-1]`）取最終 summary，取代舊 **first-match**（`re.search`）誤抓中途 progress 行；加 fail-closed 斷言 `generated >= distinct`（違反即 `raise RuntimeError`）。
- `tools/fsm_runtime/tests/test_tlc_runner_parsing.py` — 4 新測試（last-match / 正常不誤報 / 畸形 raise / 無匹配回 0；純字串、不需 Java）。

### 不變
- **無 FSM 狀態/規則變更**（`_HAPPY_PATH` 與 `*.tla` 零改動，Rule 9.18.1 不啟動）；ID_REGISTRY 維持 next_free act=173 / rule="9.39"。

### 形式化驗證
- 五軌 TLC 重跑驗證修正本身（last-match 取對 + generated ≥ distinct + 0 violation）；數據見 `EVOLUTION_LOG.md` v0.03→v0.04 段。

---

## [v0.03] - 2026-06-13（Copy-on-Evolve 自 v0.02；v0.02 凍結唯讀）

### 新增（Phase Z′ — AUTOCLAUDE_DELEGATED 觀察態落地，ACT-172；AutoSDD_improving_02 W1）
- `tools/fsm_runtime/transition_rules.py` — `_HAPPY_PATH` 新增 `AUTOCLAUDE_DELEGATED`（出邊 `{IMPLEMENTATION, ESCALATION}`）+ `OBSERVATION_STATES` 新增成員
- `tools/fsm_runtime/fsm_runtime.py` — 新增 `enter_autoclaude_delegated()` / `exit_autoclaude_delegated()`（forced-transition，比照 `enter_memory_consolidation`）
- `tools/fsm_runtime/formal/SDD_FSM.tla` — `ObservationStates` + 入/出邊 action（`T_EnterAutoclaudeDelegated` / `T_AutoDelegToImpl` / `T_AutoDelegToEsc`）+ `Next` + Fairness `SF_vars(T_AutoDelegToImpl)`（Rule 9.18.1 雙源同步）
- `workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md` — 狀態轉換表新增 AUTOCLAUDE_DELEGATED 兩出口列
- `tools/fsm_runtime/tests/test_phase_z.py` — 8 新測試（enter/exit/邊界/不變量）
- `governance/ID_REGISTRY.yaml` — 登記 ACT-172、next_free 推進 act=173

### 形式化驗證
- **五軌 TLC 重跑全綠**（SDD_FSM/META_FSM/FLEET_FSM/COMPOSITION_FSM/OPTIMIZATION_FSM）：`_HAPPY_PATH` + `SDD_FSM.tla` 變更觸發 Rule 9.18.1 義務，TLC_DISTINCT/GENERATED/DEPTH 見 EVOLUTION_LOG。

---

## [v0.02] - 2026-06-12（Copy-on-Evolve 自 v0.01；v0.01 凍結唯讀）

### 新增（Phase Z — AutoClaude 執行引擎橋接，ACT-162~171）
- `workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md` — SDD 文件 → AutoClaude playbook 標準作業（compile-then-run 兩段式）
- `agent/specialized/sdd-playbook-compiler-zh.yaml` — SDD Playbook 編譯專家角色
- `governance/rules/R-9.38-playbook-translation-fidelity.yaml` — AT↔step 100% 雙向映射保真規則（違反→SPEC_AUDIT）
- 10 場景 SOP 各加「AutoClaude 自動化執行」小節（QuickRef 同步）
- `EVOLUTION_LOG.md` — 版本演化紀錄（含 TLC 證據與回退指引）

### 修正（AutoSDD_Defect_Log 分流項）
- DEF-01-001：`governance/RULES_INDEX.md` 計數過期（35→39 檔）+ next-act/next-rule 前緣同步
- DEF-01-002：`tools/fsm_runtime/formal/run_tlc.sh` 補「五軌請走 tlc_runner.py」legacy 註記
- DEF-01-003：補 `tools/__init__.py` 顯式 package 宣告

### 形式化驗證
- `_HAPPY_PATH` / `*.tla` 零修改 → 五軌 TLC 既有證明維持有效（N/A）；
  `AUTOCLAUDE_DELEGATED` 觀察態維持提案（落地前置條件見 SDD_AUTOCLAUDE_BRIDGE.md §5）

---

## [v0.01] - 2026-04-17

### 新增（SDD 轉型）

#### SDD 核心機制
- 整合 SDD Spec-First Gate（SCG-0~SCG-6）機制，建立 7 道規格品質閘門
- 新增 SDD Core Principles（`guides/system/sdd/SDD_Core_Principles.md`）— 三大支柱定義
- 新增 SDD Guide（`guides/system/sdd/SDD_GUIDE.md`）— SDD 快速指引

#### SDD Skills（6 個新增）
- `sdd-gate` — 執行 SCG 閘門驗證（所有情境通用）
- `sdd-review` — SCG-4 PR Review 輔助，驗證實作與規格一致性
- `spec-compliance-check` — SDD 文件格式與完整性驗證
- `rtm-generate` — 生成/更新需求追溯矩陣（RTM），確保 SCG-5 100% 覆蓋
- `contract-generate` — 生成 API Contract（OpenAPI 3.1）或 Consumer-Driven Contract
- `adr-generate` — 生成 Architecture Decision Record（ADR）

#### SDD 文檔模板（51+ 個）
- 新增 `docs_template/sdd/` 目錄，含 51+ 個 SDD 專屬文檔模板
- 涵蓋：需求（PRD/FRD/Invariant Spec）、架構（SRD/C4/ADR/As-Is/Trust Boundary）、測試（RTM/Contract Test Spec/Invariant Test Contract）、規劃（Gap Analysis/PBS/Refactor Plan）、品質（Tech Debt Spec/Code Quality Baseline）、安全（SAD/STRIDE/Compliance Matrix）、部署（Pipeline Spec/IaC Spec/Runbook）等

#### SDD CI/CD 規格（9 個）
- `cicd/SDD_CICD_BASE_LAYER.md` — 基礎層（全場景通用）
- `cicd/SDD_GREENFIELD_CICD.md` — Greenfield 場景
- `cicd/SDD_BROWNFIELD_CICD.md` — Brownfield 場景
- `cicd/SDD_REFACTORING_CICD.md` — Refactoring 場景
- `cicd/SDD_TESTING_CICD.md` — Testing 場景
- `cicd/SDD_PERFORMANCE_CICD.md` — Performance 場景
- `cicd/SDD_SECURITY_CICD.md` — Security 場景
- `cicd/SDD_MIGRATION_CICD.md` — Migration 場景
- `cicd/SDD_INTEGRATION_CICD.md` — Integration 場景

#### SDD 場景增強文件（10 個）
- 新增各情境 `SDD_{SCENARIO}_ENHANCEMENT.md`，定義 SDD Spec-First 流程補強
- 涵蓋全部 10 大情境：greenfield / brownfield / refactoring / documentation / devops / integration / migration / performance / security / testing

#### 文檔目錄結構（SDD 8 層）
- `docs/01_requirements/` — PRD / FRD / Invariant Spec / Third-Party API Research
- `docs/02_architecture/` — SRD / C4 / ADR / As-Is / Trust Boundary Map
- `docs/02_architecture/adr/` — ADR-{NNN} 架構決策記錄
- `docs/02_architecture/api/` — OpenAPI 3.1 Contract / Consumer Contract
- `docs/03_testing/` — RTM / Test Plan / Test Strategy / Defect Classification
- `docs/03_testing/contracts/` — Invariant Test Contract / Contract Test Spec / Chaos Contract
- `docs/04_planning/` — Gap Analysis / Refactor Plan
- `docs/04_planning/performance/` — Performance Baseline Spec（PBS）
- `docs/05_development/` — Living Doc Strategy
- `docs/06_quality/` — Code Quality Baseline / Tech Debt Spec
- `docs/06_quality/security/` — SAD / STRIDE / Compliance Matrix / Asset Inventory
- `docs/07_design/` — UI/UX / Database Design
- `docs/08_deployment/` — CI/CD Pipeline Spec / Monitoring Alert Spec / Release Notes / Runbook / Cutover Plan
- `docs/08_deployment/iac/` — IaC Specifications

---

### 修改（v0.09 → v0.01 升級）

#### Agents（21 個全部更新）
- 21 個 Agents 版本更新至 v0.01（7 core + 14 specialized）
- 核心 Agents 新增 SDD 技能：
  - `sa-analyst`：逆向規格工程（As-Is SRD）、Gap Analysis、Business Invariants 提取（INV-XXX）
  - `sd-architect`：As-Is C4 Model、ADR Archaeology、Before/After 架構對比、Migration Contract Map
  - `qa-tester`：As-Is 測試規格基線、Invariant Test Contract、Consumer Contract 測試
  - `dev-developer`：Strangler Fig 模式、Branch by Abstraction、Contract-First 開發
  - `code-analyzer`：Tech Debt 規格化（TD-XXX）、Code Quality Baseline Spec
  - `technical-writer`：Living Documentation 策略、ADR 維護、API 文件從 Contract 生成

#### Workflows（23 個全部更新）
- 所有 23 個 Workflows 整合 SCG 閘門驗證點
- 新增 SDD Spec-First Gate Workflow（`workflow/sdd-spec-first-gate/`）
- 核心 8 個 Workflow + 13 個場景特定 Workflow + 1 個 ADR Workflow

#### 場景 SOP（10 個全部更新）
- 所有 10 個場景 SOP 反映 SDD Spec-First 流程
- 每個場景新增強制 SCG 閘門步驟說明
- Brownfield / Refactoring / Migration 場景新增逆向規格工程步驟

#### 工具與腳本
- `tools/init_project.sh` 新增 `--sdd` 模式（v3.3-SDD），自動建立 SDD 8 層 docs/ 目錄結構

#### 指南文件更新
- `guides/user/onboarding/QUICK_START_GUIDE.md` — 新增 SDD 三大支柱說明與 SCG 閘門引導
- `guides/user/onboarding/SCENARIO_DECISION_TREE.md` — 各情境新增對應 SCG 閘門說明
- `guides/user/standards/PROJECT_DOCUMENTATION_STANDARDS.md` — 目錄結構更新為 SDD 8 層，FILE_DIRECTORY_RULES.md 引用
- `agent/AGENT_COLLABORATION_PATTERNS.md` — 新增「SDD SCG 閘門協作模式」章節
- `agent/AGENT_PHASE2_UPDATE_GUIDE.md` — 更新為 v0.09 → v0.01 升級指南
- `scenarios/SCENARIO_TRANSITION_GUIDE.md` — 新增「場景切換前的 SCG 驗證」強制章節
- `scenarios/SCENARIO_AGENT_MAPPING.md` — 新增各情境 SCG 對照說明與特殊情境說明

---

### 歸檔

- AISDLC v0.09 保留於 `AISDLC_v0.09/` 目錄（僅供參考，不修改）
- v0.09 版本歷史已歸檔至 `build/planning/archive/SDD_VERSION_HISTORY.md`

---

## [v0.09] - 2026-04-14（歸檔）

> 此版本為 AISDLC 開發專注版（Development-Focused Edition），版本歷史已歸檔至 `build/planning/archive/SDD_VERSION_HISTORY.md`。
>
> v0.09 定義了 10 大情境、21 個 Agents、23 個 Workflows 的基礎框架，v0.01 在此基礎上加入 SDD Spec-First Gate 機制完成框架轉型。

### 主要特性（v0.09 歸檔記錄）
- 10 大開發情境（含 migration）
- 21 個 Agents（7 core + 14 specialized）
- 23 個 Workflows
- 雙層 guides 架構（system + user）
- 中文優先 Agents（-zh.yaml）
- 開發專注版 docs/ 目錄結構（8 個目錄）
