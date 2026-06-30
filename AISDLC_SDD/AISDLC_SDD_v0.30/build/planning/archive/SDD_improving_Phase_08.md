# SDD 改善報告 — Phase 08：深度內容審查（第二輪）

**報告日期**: 2026-04-16
**審查範圍**: AISDLC_v0.09 vs AISDLC_SDD_v0.01 第二輪比對（Phase 07 驗證 + 新問題發現）
**審查方法**: 檔案結構比對 + 內容版本標識掃描 + 路徑完整性驗證
**前次報告**: `build/planning/archive/SDD_improving_Phase_07.md`（2026-04-15，已歸檔）

---

## 審查摘要

Phase 07 已處理目錄結構層面的缺失（prompts/、scenarios 跨場景指南、版本控管文件等）。  
本次審查聚焦於**內容層面**的殘留問題：版本標識、路徑引用、跨文件一致性。

| 類別 | Phase 07 狀態 | Phase 08 新發現 | 嚴重度 |
|------|-------------|---------------|-------|
| 1. Agent | 結構完整 | ❌ Specialized agents 版本仍為 v0.09；template_path 路徑錯誤 | 🔴 高 |
| 2. Skills | 新增 6 個 SDD Skills | ✅ 無新問題 | 🟢 |
| 3. Scenarios | 跨場景指南補齊 | ❌ SOP 文件含大量 v0.09 引用（202 處）；migration 缺 SOP_DeepDive.md | 🟡 中 |
| 4. Workflow | 加入 SCG 節點 | ❌ 所有 21 個 workflow 版本標識仍為 v0.09 | 🔴 高 |
| 5. Guides | 完整 + SDD 指引 | ❌ guides/ 殘留 291 處 v0.09 引用 | 🟡 中 |
| 6. Prompts | 目錄已建立 | ✅ 內容已更新為 SDD 版本 | 🟢 |
| 7. Templates | sdd/ 目錄完整 | ❌ docs_template/prd/ 與 core/prd/ 重複 MVP 模板 | 🟡 中 |
| 8. Tools | init scripts 已更新 | ✅ 無新問題 | 🟢 |
| 9. 版本控管 | SOP + CheckList 已建立 | ✅ 完整 | 🟢 |
| 10. 目錄/CLAUDE.md | FILE_DIRECTORY_RULES 已補充 | ❌ CLAUDE.md 場景數量描述過時（4→10）；Agent 載入規則不完整 | 🔴 高 |

---

## 詳細差異清單

---

### 1. Agent（🔴 高優先）

#### 1-A：Specialized Agent 版本標識未更新

**問題**：10 個 specialized agent YAML 檔案，`agent.version` 仍為 `"v0.09"`。

受影響檔案：
```
agent/specialized/code-analyzer-zh.yaml        → version: "v0.09"
agent/specialized/dev-senior-zh.yaml           → version: "v0.09"
agent/specialized/devops-engineer-zh.yaml      → version: "v0.09"
agent/specialized/integration-specialist-zh.yaml → version: "v0.09"
agent/specialized/qa-automation-zh.yaml        → version: "v0.09"
agent/specialized/qa-lead-zh.yaml              → version: "v0.09"（待確認）
agent/specialized/qa-mobile-tester-zh.yaml     → 待確認
agent/specialized/qa-web-tester-zh.yaml        → 待確認
agent/specialized/sd-mobile-architect-zh.yaml  → 待確認
agent/specialized/sd-web-architect-zh.yaml     → 待確認
agent/specialized/performance-engineer-zh.yaml → 待確認
agent/specialized/security-engineer-zh.yaml    → 待確認
agent/specialized/technical-writer-zh.yaml     → 待確認
agent/specialized/compliance-officer-zh.yaml   → 待確認
```

#### 1-B：Agent README.md 版本標識未更新

`agent/README.md`：
- 第 80 行：`v0.09 起全部中文化` — 表述為歷史記錄可接受，但：
- 第 197 行：`### v0.09 (2026-03-20)` — 缺少 v0.01-SDD 版本段落
- 第 248 行：`**版本**：v0.09` — 應更新為 v0.01

#### 1-C：Agent template_path 引用路徑錯誤

`04.sa-analyst-zh.yaml`（第 84、189 行）：
```yaml
template_path: "../docs_template/frd/FRD_Module_Template.md"  # ❌ 路徑不存在
```
正確路徑應為：`../docs_template/core/frd/FRD_Universal_Template.md`

`05.sd-architect-zh.yaml`（第 86、197 行）：
```yaml
template_path: "../docs_template/srd/SRD_Module_Template.md"  # ❌ 路徑不存在（srd/ 已移至 core/srd/）
```
正確路徑應為：`../docs_template/core/srd/SRD_Module_Template.md`

`01.agent-template-zh.yaml`（第 175、176 行）：
```yaml
# - ../docs_template/frd/FRD_Module_Template.md  # FRD 模板（已注釋但路徑錯誤）
# - ../docs_template/srd/SRD_Module_Template.md  # SRD 模板（已注釋但路徑錯誤）
```

#### 改善行動
- [ ] **A08-01**: 更新所有 specialized agent YAML 的 `agent.version` 從 `v0.09` 到 `v0.01`
- [ ] **A08-02**: 更新 `agent/README.md`：補充 `### v0.01 (2026-04-16)` 版本段落，修正版本號
- [ ] **A08-03**: 修正 `04.sa-analyst-zh.yaml` template_path → `../docs_template/core/frd/FRD_Universal_Template.md`
- [ ] **A08-04**: 修正 `05.sd-architect-zh.yaml` template_path → `../docs_template/core/srd/SRD_Module_Template.md`
- [ ] **A08-05**: 修正 `01.agent-template-zh.yaml` 的注釋路徑

---

### 2. Skills（🟢 無新問題）

Phase 07 已完成：
- 新增 `sdd-review` skill
- 核心 skills SDD 對齊驗證完成

無新發現。

---

### 3. Scenarios（🟡 中優先）

#### 3-A：SOP 文件含大量 v0.09 引用

`scenarios/` 目錄掃描發現 **202 處** `v0.09` 或 `AISDLC v0.09` 引用，主要集中在：
- 各場景 `SOP.md`、`SOP_DeepDive.md`、`SOP_QuickRef.md` 的 header/metadata
- 場景 README 的版本說明

這些文件的主體內容已包含 SDD 元素（Phase 07 加入了 SCG 節點說明），但 metadata 版本標識未同步更新。

#### 3-B：migration 場景缺少 SOP_DeepDive.md

`scenarios/migration/` 目錄：
```
✅ SOP.md
✅ SOP_QuickRef.md
✅ SDD_MIGRATION_ENHANCEMENT.md
❌ SOP_DeepDive.md（缺失）
```
v0.09 原本就缺少此檔案，SDD 轉換時未補充。

#### 改善行動
- [ ] **SC08-01**: 批次更新 `scenarios/` 各 SOP 文件 metadata 中的版本標識（v0.09 → v0.01）
- [ ] **SC08-02**: 建立 `scenarios/migration/SOP_DeepDive.md`（詳細執行步驟，對應 SDD_MIGRATION_ENHANCEMENT）

---

### 4. Workflow（🔴 高優先）

#### 問題：所有 21 個 Workflow 檔案版本標識未更新

掃描結果：`workflow/core/` + `workflow/scenario-specific/` 共 **21 個 .md 檔案**，全部含有：

```yaml
# AISDLC v0.09 執行配置
workflow_metadata:
  version: "v0.09"
```

Phase 07 的 W-01 動作（加入 SDD SCG 閘門整合說明節）已執行，但 **版本 metadata 未更新**。  
這造成使用者讀取時產生混淆，不知是否為 SDD 版本。

受影響檔案清單（21 個）：
```
workflow/core/api-specification.md
workflow/core/change-management.md
workflow/core/consistency-check.md
workflow/core/interaction-analysis.md
workflow/core/requirements-extraction.md
workflow/core/sprint-execution.md
workflow/core/user-story-design.md
workflow/core/validation-documentation.md
workflow/scenario-specific/brownfield-analysis-flow.md
workflow/scenario-specific/code-analysis-flow.md
workflow/scenario-specific/devops-setup-flow.md
workflow/scenario-specific/documentation-flow.md
workflow/scenario-specific/documentation-reconstruction-flow.md
workflow/scenario-specific/greenfield-complete-flow.md
workflow/scenario-specific/integration-analysis-flow.md
workflow/scenario-specific/migration-planning-flow.md
workflow/scenario-specific/performance-optimization-flow.md
workflow/scenario-specific/refactoring-planning-flow.md
workflow/scenario-specific/security-assessment-flow.md
workflow/scenario-specific/tech-stack-selection-flow.md
workflow/scenario-specific/testing-strategy-flow.md
```

#### 改善行動
- [ ] **W08-01**: 批次將所有 workflow `.md` 檔案中的 `# AISDLC v0.09 執行配置` → `# AISDLC-SDD v0.01 執行配置`
- [ ] **W08-02**: 批次將 `version: "v0.09"` → `version: "v0.01"` in workflow_metadata

---

### 5. Guides（🟡 中優先）

#### 問題：guides/ 殘留 291 處 v0.09 引用

主要來源：
- `guides/user/sample/` — 21 個場景範例文件中的版本說明、框架路徑引用（如 `AISDLC_v0.09/` → 應改為 `AISDLC_SDD_v0.01/`）
- `guides/user/onboarding/` — 入門指南中的版本號
- `guides/system/` — 系統指南中的版本引用

Phase 07 G-01 說「21 個指南已加入 SDD v0.01 使用者提示說明」，但舊的 v0.09 路徑引用仍存在（因為是加入說明，而非替換）。

#### 改善行動
- [ ] **G08-01**: 更新 `guides/user/sample/` 各文件，將框架路徑從 `AISDLC_v0.09/` 替換為 `AISDLC_SDD_v0.01/`
- [ ] **G08-02**: 更新 `guides/user/onboarding/` 版本引用

---

### 6. Prompts（🟢 無新問題）

Phase 07 已建立完整 prompts/ 目錄且內容為 SDD 原生版本。

---

### 7. Templates（🟡 中優先）

#### 問題：MVP_Definition_Template.md 重複

同一檔案存在於兩個位置：
```
docs_template/prd/MVP_Definition_Template.md          ← 根層路徑（舊位置，Phase 07 補充）
docs_template/core/prd/MVP_Definition_Template.md     ← 正規位置（Phase 07 已存在）
```

這造成目錄規則不一致：`FILE_DIRECTORY_RULES.md` 規定模板應在 `docs_template/core/prd/`，但根層仍有舊版。

#### 改善行動
- [ ] **T08-01**: 確認 `docs_template/prd/MVP_Definition_Template.md`（根層）內容是否與 `core/prd/` 版本一致
- [ ] **T08-02**: 若一致，移除根層重複檔案；若不一致，合併後移除

---

### 8. Tools（🟢 無新問題）

`init_project.sh` 和 `init_project.ps1` 已更新至 `v3.3-SDD`，支援 `--sdd` 旗標。  
`verify_traceability.sh` 已存在。

---

### 9. 版本控管（🟢 Phase 07 完成）

以下文件均已建立：
- `AISDLC_SDD_UPGRADE_SOP.md` ✅
- `AISDLC_SDD_UPGRADE_CHECKLIST.md` ✅
- `SDD_VERSION_HISTORY.md` ✅
- `releases/v0.01/RELEASE_NOTES_v0.01.md` ✅

---

### 10. 目錄結構 / CLAUDE.md（🔴 高優先）

#### 問題：CLAUDE.md 場景描述過時

`CLAUDE.md`（專案根目錄）第 44 行：
```
│   ├── scenarios/                     ← 4 場景（greenfield/brownfield/refactoring/documentation）
```
**實際現況**：v0.01 scenarios/ 已包含 **10 個場景**（+devops/integration/migration/performance/security/testing 各有 SDD Enhancement）。

#### 問題：CLAUDE.md Agent 載入規則描述不完整

`CLAUDE.md` 第 198 行：
```
2. 根據場景（greenfield/brownfield/refactoring）自動載入 Primary Agents
```
應更新為 10 個 SDD 場景。

#### 問題：CLAUDE.md 場景對應表不完整

`CLAUDE.md` Rule 3「場景對應」段落只列出 4 個場景，缺少：
```
| DevOps      | CI/CD 規格驅動   | `scenarios/devops/SDD_DEVOPS_ENHANCEMENT.md` |
| Integration | API Contract    | `scenarios/integration/SDD_INTEGRATION_ENHANCEMENT.md` |
| Migration   | 遷移規格         | `scenarios/migration/SDD_MIGRATION_ENHANCEMENT.md` |
| Performance | PBS Gate        | `scenarios/performance/SDD_PERFORMANCE_ENHANCEMENT.md` |
| Security    | STRIDE 驅動     | `scenarios/security/SDD_SECURITY_ENHANCEMENT.md` |
| Testing     | Contract 覆蓋   | `scenarios/testing/SDD_TESTING_ENHANCEMENT.md` |
```

#### 改善行動
- [ ] **D08-01**: 更新 `CLAUDE.md` 第 44 行：`4 場景` → `10 場景`，補充場景清單
- [ ] **D08-02**: 更新 `CLAUDE.md` Rule 3 場景對應表，補充 6 個新場景的 Enhancement 路徑
- [ ] **D08-03**: 更新 `CLAUDE.md` Rule 6 第 198 行，Agent 載入場景描述更新為 10 個場景

---

## 改善優先級匯總

### 🔴 高優先（影響使用正確性）

| ID | 項目 | 影響 |
|----|------|------|
| W08-01~02 | 21 個 workflow 版本標識更新 | 使用者混淆 v0.09/v0.01 |
| D08-01~03 | CLAUDE.md 場景描述更新（4→10） | 新場景 SDD Enhancement 路徑找不到 |
| A08-03~04 | Agent template_path 路徑錯誤修正 | Agent 載入模板時路徑 404 |

### 🟡 中優先（品質改善）

| ID | 項目 | 影響 |
|----|------|------|
| A08-01~02 | Specialized agent 版本標識更新 | 一致性 |
| SC08-01 | Scenarios SOP 版本標識批次更新 | 一致性 |
| SC08-02 | 補充 migration/SOP_DeepDive.md | 完整性 |
| G08-01~02 | Guides 路徑引用更新 | 使用者查閱正確路徑 |
| T08-01~02 | MVP 模板重複問題處理 | 目錄規則一致性 |

### 🟢 低優先（可延後）

| ID | 項目 | 影響 |
|----|------|------|
| A08-05 | agent-template 注釋路徑修正 | 微小 |

---

## 工作量估計

| 優先級 | 項目數 | 估計 |
|-------|-------|------|
| 🔴 高優先 | 7 項 | 0.5 個工作日（大多為批次替換） |
| 🟡 中優先 | 9 項 | 1 個工作日 |
| 🟢 低優先 | 1 項 | 30 分鐘 |

---

## Next Actions

建議下一步執行順序（Phase 09）：

1. **W08-01~02**：批次更新 21 個 workflow 版本 metadata（sed 批次替換，快速完成）
2. **D08-01~03**：更新 CLAUDE.md 場景描述（影響使用者每次互動）
3. **A08-03~04**：修正 Agent template_path（避免 Agent 引用不存在路徑）
4. **A08-01~02**：更新 Specialized Agent 版本號 + README
5. **SC08-01**：批次更新 scenarios SOP 版本標識
6. **T08-01~02**：處理 MVP 模板重複

---

*報告由 Claude Code 自動生成 | 基於 AISDLC_SDD_v0.01 框架二輪審查*
