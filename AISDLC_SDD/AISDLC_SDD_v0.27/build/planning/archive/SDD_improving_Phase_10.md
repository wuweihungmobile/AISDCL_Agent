# SDD 轉換改善報告 — Phase 10

**產出日期**: 2026-04-17
**比對基準**: AISDLC v0.09 vs AISDLC-SDD v0.01
**目的**: 識別 SDD 轉換過程中的遺漏、版本殘留與一致性問題
**後續行動**: ✅ 已歸檔（Phase 10 全部驗證完成 2026-04-19）

---

## 執行摘要

| 類別 | 狀態 | 嚴重度 | 問題數 |
|------|------|--------|--------|
| 1. Agent | ⚠️ 部分遺漏 | 中 | 3 |
| 2. Skills | ✅ 基本完整 | 低 | 1 |
| 3. Scenarios | ⚠️ 大量殘留 | 高 | 3 |
| 4. Workflow | ❌ 嚴重殘留 | 高 | 2 |
| 5. Guides | ⚠️ 大量殘留 | 中 | 2 |
| 6. Prompts | ✅ 完整更新 | — | 0 |
| 7. Templates | ⚠️ 部分殘留 | 低 | 2 |
| 8. Tools | ✅ 基本完整 | 低 | 1 |
| 9. 版本控管 | ⚠️ 待確認 | 中 | 2 |
| 10. 目錄結構紀錄 | ❌ 遺漏檔案 | 高 | 2 |

---

## 1. Agent

### ✅ 已完成
- 7 個 Core Agents 全部完成 SDD 技能擴充（04.sa-analyst, 05.sd-architect, 07.qa-tester 等）
- `agent/core/` 全部正確更新至 v0.01

### ⚠️ 問題

**A1 — 10 個 Specialized Agent 仍殘留 v0.09 版本標記**

受影響檔案（`agent/specialized/`）：
- `code-analyzer-zh.yaml`
- `dev-senior-zh.yaml`
- `devops-engineer-zh.yaml`
- `integration-specialist-zh.yaml`
- `qa-automation-zh.yaml`
- `qa-lead-zh.yaml`
- `qa-mobile-tester-zh.yaml`
- `qa-web-tester-zh.yaml`
- `sd-mobile-architect-zh.yaml`
- `security-engineer-zh.yaml`

> 這些 Specialized Agents 僅改版本號，未必需要 SDD 技能擴充，但版本標記應一致。

**A2 — `AGENT_PHASE2_UPDATE_GUIDE.md` 未更新**

內容完全相同於 v0.09，未反映 SDD 升級路徑。

**A3 — `AGENT_COLLABORATION_PATTERNS.md` 未更新**

未加入 SDD SCG 閘門協作模式說明（如 SCG-0 前 SA+BA 協作、SCG-4 時 Dev+QA 協作）。

---

## 2. Skills

### ✅ 已完成
- 6 個新 SDD Skills 正確新增：`sdd-gate`, `sdd-review`, `spec-compliance-check`, `rtm-generate`, `contract-generate`, `adr-generate`
- 新增 `SKILL_STANDARD_TEMPLATE.md` ✅
- 所有 35 個繼承 Skills 保留完整

### ⚠️ 問題

**S1 — `SKILL_DEVELOPMENT_PLAN.md` 仍引用 `AISDLC_v0.09` 路徑**

第 1 個殘留：`.claude/skills/SKILL_DEVELOPMENT_PLAN.md` 引用舊版路徑，應更新為 `AISDLC_SDD_v0.01`。

---

## 3. Scenarios

### ✅ 已完成
- 10 個場景的 `SDD_*_ENHANCEMENT.md` 全部存在或更新
- `scenarios/` 根目錄結構保留完整（`SCENARIO_AGENT_MAPPING.md` 等）

### ⚠️ 問題

**SC1 — 44 個場景 .md 檔仍殘留 v0.09 版本字串**

主要受影響（各場景的 `SOP.md`, `SOP_DeepDive.md`, `SOP_QuickRef.md`）：
- `brownfield/SOP.md`、`SOP_DeepDive.md`、`SOP_QuickRef.md`
- `greenfield/SOP.md`、`SOP_DeepDive.md`、`SOP_QuickRef.md`、`Parallel_Execution_Guide.md`
- `devops/SOP.md`、`SOP_DeepDive.md`、`SOP_QuickRef.md`
- `documentation/SOP.md`、`SOP_DeepDive.md`、`SOP_QuickRef.md`
- `integration/`, `migration/`, `performance/`, `refactoring/`, `security/`, `testing/` 同上
- 根層 `ERROR_RECOVERY_GUIDE.md`, `FRONTEND_SPECIFIC_GUIDE.md`, `SCALING_GUIDE.md`, `SCENARIO_TRANSITION_GUIDE.md`

**SC2 — `brownfield/SOP.md:353` 引用不存在檔案**

```
# SOP.md 第 353 行
> 各階段產出文件必須依據 [DEVELOPMENT_DIRECTORY_STRUCTURE.md](../../guides/user/onboarding/DEVELOPMENT_DIRECTORY_STRUCTURE.md) 存放至正確目錄。
```
SDD v0.01 中該檔案已不存在（由 `FILE_DIRECTORY_RULES.md` 取代），但連結未更新。

**SC3 — `SCENARIO_TRANSITION_GUIDE.md` / `SCENARIO_AGENT_MAPPING.md` 未加入 SDD SCG 流程**

這兩份根層指南仍是 v0.09 邏輯，未反映 SCG 閘門在場景切換時的強制驗證。

---

## 4. Workflow

### ✅ 已完成
- `workflow/core/` 全部 8 個檔案正確更新至 v0.01 ✅
- `workflow/adr-generation/ADR_GENERATION.md` 存在 ✅
- `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md` 存在 ✅

### ❌ 嚴重問題

**W1 — 11 個 scenario-specific workflow 仍殘留 v0.09**

| 檔案 | 狀態 |
|------|------|
| `greenfield-complete-flow.md` | ❌ 版本標記仍為 `v0.09`，內容未更新 |
| `code-analysis-flow.md` | ⚠️ 已加 SCG 段落，但版本標記缺失 |
| `devops-setup-flow.md` | ⚠️ 已加 SCG 段落，但版本標記缺失 |
| `documentation-flow.md` | ⚠️ 仍有 `⭐ v0.09 新增` 字串 |
| `integration-analysis-flow.md` | ⚠️ 已加 SCG 段落，但版本標記缺失 |
| `refactoring-planning-flow.md` | ⚠️ 已加 SCG 段落，但版本標記缺失 |
| `security-assessment-flow.md` | ⚠️ 已加 SCG 段落，但版本標記缺失 |
| `tech-stack-selection-flow.md` | ⚠️ 已加 SCG 段落，但版本標記缺失 |
| `testing-strategy-flow.md` | ⚠️ 已加 SCG 段落，但版本標記缺失 |

`greenfield-complete-flow.md` 最為嚴重，內容完全未更新（仍是 v0.09 原文，無 SCG 閘門整合）。

**W2 — Scenario-specific workflow 缺少版本一致性規範**

有些 workflow 用 YAML frontmatter `version: "v0.01"`，有些用 Markdown body `**版本**: v0.09`，兩種格式並存。

---

## 5. Guides

### ✅ 已完成
- 新增 `guides/system/sdd/SDD_GUIDE.md` ✅
- 新增 `guides/system/sdd/SDD_Core_Principles.md`（從根目錄移入）✅

### ⚠️ 問題

**G1 — 50 個 guides 檔案仍殘留 v0.09 版本字串**

主要受影響目錄：
- `guides/system/agent/`, `api/`, `architecture/`, `naming/`, `planning/`, `quality/`, `testing/`（共 17 個）
- `guides/user/onboarding/`（8 個：QUICK_START_GUIDE.md, PROJECT_INITIALIZATION_GUIDE.md 等）
- `guides/user/sample/`（22 個）
- `guides/README.md`、`guides/system/README.md`

**G2 — Onboarding 指南未反映 SDD Spec-First 流程**

`guides/user/onboarding/` 下所有文件（QUICK_START_GUIDE.md、SCENARIO_DECISION_TREE.md、TUTORIAL_MODE.md 等）仍以 v0.09 邏輯引導使用者，未加入 SCG 閘門說明、SDD 三大支柱介紹。

---

## 6. Prompts

### ✅ 完整更新
- 所有 prompts 已更新為 SDD v0.01 格式
- 版本標記和載入路徑均已更新
- **無問題**

---

## 7. Templates

### ✅ 已完成
- 51+ 個新 SDD 專屬模板（`docs_template/sdd/`）完整建立 ✅
- `docs_template/core/` 結構維持不變 ✅
- `docs_template/scenario_specific/` 結構維持不變 ✅

### ⚠️ 問題

**T1 — 36 個模板檔案仍殘留 v0.09 版本字串**

主要在 `docs_template/core/`、`docs_template/scenario_specific/`、`docs_template/support/` 的舊有模板。

**T2 — `docs_template/` 根層結構不一致**

v0.09 有 `docs_template/prd/` 和 `docs_template/srd/` 兩個根層目錄，SDD v0.01 已移除（整合入 `docs_template/core/`），但 `docs_template/README.md` 是否同步更新需確認。

---

## 8. Tools

### ✅ 已完成
- `init_project.sh` 更新至 v3.3-SDD（新增 `--sdd` 模式）✅
- `init_project.ps1` 同步更新 ✅
- `AISDLC_CLAUDE_RULES.md` 更新至 v2.0-SDD ✅
- `PROJECT_CLAUDE_Template.md` 更新至 v2.1-SDD ✅
- `verify_traceability.sh` 更新至 v1.1-SDD（更新路徑至 SDD）✅

### ⚠️ 問題

**TO1 — `tools/README.md` 是否更新？**

`tools/README.md` 需確認是否已更新為 SDD 版本，描述正確的工具用途與 `--sdd` 使用方式。

---

## 9. 版本控管

### ✅ 已完成
- `SDD_VERSION_HISTORY.md` 已移入 `build/planning/archive/` ✅
- `releases/v0.01/RELEASE_NOTES_v0.01.md` 存在 ✅
- `SDD_Core_Principles.md` 從根目錄移至 `guides/system/sdd/` ✅

### ⚠️ 問題

**V1 — Git 狀態有未 commit 的變更**

目前 git status 顯示：
- `D AISDLC_SDD_v0.01/SDD_Core_Principles.md` — 刪除未 commit
- `D AISDLC_SDD_v0.01/SDD_VERSION_HISTORY.md` — 刪除未 commit
- 多個 `M` 修改未 commit

需決定是否在 Phase 10 前執行 commit，確保版本狀態清楚。

**V2 — 缺少框架版本追蹤頂層檔案**

v0.09 的 `SDD_VERSION_HISTORY.md` 已歸檔，但 SDD v0.01 沒有對等的版本歷史追蹤機制。建議在根目錄或 `releases/` 建立 `CHANGELOG.md` 或在 `AISDLC_SDD_INIT.md` 內嵌版本歷史。

---

## 10. 目錄結構紀錄

### ✅ 已完成
- `FILE_DIRECTORY_RULES.md` 存在且完整記錄 SDD 目錄規範 ✅
- `docs/` 8 層子目錄結構建立（含 `.gitkeep`）✅
- `cicd/` 9 個 SDD CI/CD 規格建立 ✅

### ❌ 嚴重問題

**D1 — `DEVELOPMENT_DIRECTORY_STRUCTURE.md` 遺漏**

v0.09 根目錄有 `DEVELOPMENT_DIRECTORY_STRUCTURE.md`，SDD v0.01 已移除，但以下兩處仍引用：

1. `scenarios/brownfield/SOP.md:353` — 連結指向 `../../guides/user/onboarding/DEVELOPMENT_DIRECTORY_STRUCTURE.md`（不存在）
2. `guides/user/standards/PROJECT_DOCUMENTATION_STANDARDS.md:502,508,513` — 多處引用此檔名

> **處理方案**：更新上述引用，改指向 `FILE_DIRECTORY_RULES.md`（SDD 的對等替代）。

**D2 — `guides/user/standards/PROJECT_DOCUMENTATION_STANDARDS.md` 需同步更新**

該檔案仍以 v0.09 邏輯說明目錄結構，未反映 SDD `docs/01_requirements/` 到 `docs/08_deployment/` 的新 8 層結構及 SDD 特有子目錄（`02_architecture/adr/`, `02_architecture/api/` 等）。

---

## 優先修復建議

### P0 — 立即修復（功能性破壞）

| # | 問題 | 動作 |
|---|------|------|
| D1 | `brownfield/SOP.md` 引用不存在檔案 | 更新連結至 `FILE_DIRECTORY_RULES.md` |
| W1-A | `greenfield-complete-flow.md` 完全未更新 | 加入 SCG 閘門整合段落，更新版本至 v0.01 |

### P1 — 高優先（一致性問題）

| # | 問題 | 動作 |
|---|------|------|
| W1-B | 其餘 10 個 scenario-specific workflow 版本標記不一致 | 統一版本標記格式並確認 SCG 段落完整 |
| SC1 | 44 個 scenario SOP 版本殘留 | 批次更新版本字串 |
| A1 | 10 個 Specialized Agent YAML 版本殘留 | 批次更新版本字串 |

### P2 — 中優先（完整性提升）

| # | 問題 | 動作 |
|---|------|------|
| G2 | Onboarding 指南未反映 SDD 流程 | 更新 QUICK_START_GUIDE.md、SCENARIO_DECISION_TREE.md |
| D2 | `PROJECT_DOCUMENTATION_STANDARDS.md` 結構過時 | 更新 8 層 SDD 目錄說明 |
| A3 | `AGENT_COLLABORATION_PATTERNS.md` 缺 SCG 協作模式 | 新增 SCG 閘門協作模式段落 |
| V2 | 缺頂層版本追蹤 | 在 AISDLC_SDD_INIT.md 或 releases/ 建立 CHANGELOG |

### P3 — 低優先（整潔性）

| # | 問題 | 動作 |
|---|------|------|
| G1 | 50 個 guides 版本字串殘留 | 批次更新版本字串 |
| T1 | 36 個 template 版本字串殘留 | 批次更新版本字串 |
| S1 | `SKILL_DEVELOPMENT_PLAN.md` 路徑殘留 | 更新路徑至 AISDLC_SDD_v0.01 |
| V1 | Git 未提交變更 | 執行 commit 清理狀態 |

---

## 數量統計

| 類別 | v0.09 引用殘留數 | 嚴重遺漏數 |
|------|----------------|-----------|
| Agent YAML | 10 | 0 |
| Skills | 1 | 0 |
| Scenarios | 44 | 2（含斷連結） |
| Workflow scenario-specific | 11 | 1（greenfield 未更新） |
| Guides | 50 | 1（onboarding SDD化） |
| Prompts | 0 | 0 |
| Templates | 36 | 0 |
| Tools | 0 | 0 |
| **總計** | **152** | **4** |
