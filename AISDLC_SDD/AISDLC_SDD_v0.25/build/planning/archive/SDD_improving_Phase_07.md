# SDD 改善報告 — Phase 07：框架完整性審查

**報告日期**: 2026-04-15
**審查範圍**: AISDLC_v0.09 vs AISDLC_SDD_v0.01 全面比對
**審查方法**: 目錄結構逐項比對 + 檔案清單差異分析
**狀態**: ✅ 完成（2026-04-15）

---

## 審查摘要

| 類別 | v0.09 狀態 | SDD v0.01 狀態 | 差異等級 |
|------|-----------|---------------|---------|
| 1. Agent | 7 core + 14 specialized + backup_en | 7 core + 14 specialized（無 backup_en） | 🟡 中 |
| 2. Skills | 36 skills | 41 skills（+5 SDD 專屬） | 🟢 良好，待內容審查 |
| 3. Scenarios | 10 scenarios + 5 跨場景指南 | 10 scenarios，缺跨場景指南 | 🔴 高 |
| 4. Workflow | 8 core + 13 scenario-specific | 8 core + 13 scenario-specific | 🟢 完整 |
| 5. Guides | 完整（含 system/user） | 完整 + 新增 sdd/ 類別 | 🟢 完整 |
| 6. Prompts | 有 prompts/ 目錄（3 子目錄） | ❌ 完全缺失 | 🔴 高 |
| 7. Templates | core + scenario_specific + support | 同上 + sdd/（60+ 新模板）；缺 prd/MVP | 🟡 中 |
| 8. Tools | init scripts | init scripts + verify_traceability.sh | 🟡 缺 releases/ 和版本文件 |
| 9. 版本控管 | 有 UPGRADE_SOP + CheckList | ❌ 完全缺失 | 🔴 高 |
| 10. 目錄結構紀錄 | DEVELOPMENT_DIRECTORY_STRUCTURE.md | FILE_DIRECTORY_RULES.md（替代） | 🟡 中 |

---

## 詳細差異清單

---

### 1. Agent

#### 現況
- SDD v0.01: `agent/core/`（7 files）、`agent/specialized/`（14 files）
- v0.09: 同上 + `backup_en/` 子目錄（英文備份版本）

#### 發現缺失

| 項目 | v0.09 | SDD v0.01 | 處理建議 |
|-----|-------|-----------|---------|
| `agent/core/README.md` | ✅ 存在 | ❌ 缺失 | 補充 |
| `agent/specialized/README.md` | ✅ 存在 | ❌ 缺失 | 補充 |
| `backup_en/` 英文備份 | ✅ core + specialized 各有 | ❌ 已移除 | 評估是否需要（SDD 以中文為主可接受） |

#### 改善行動
- [x] **A-01**: 補充 `agent/core/README.md`（載入說明 + SDD 角色說明）✅ 2026-04-15
- [x] **A-02**: 補充 `agent/specialized/README.md`（選用指引 + SDD 技能對應）✅ 2026-04-15
- [x] **A-03**: 評估 backup_en/ 是否需恢復 — 決策：不恢復（SDD 以中文為主，無多語需求）✅ 2026-04-15

---

### 2. Skills

#### 現況
- v0.09: 36 skills
- SDD v0.01: 41 skills（新增 5 個 SDD 專屬）

#### 新增 SDD Skills（正向）
| Skill | 功能 |
|-------|------|
| `adr-generate` | ADR 自動生成 |
| `contract-generate` | API Contract 生成 |
| `rtm-generate` | 需求追蹤矩陣生成 |
| `sdd-gate` | SCG 閘門驗證 |
| `spec-compliance-check` | 規格合規性檢查 |

#### 發現待改善

| 項目 | 說明 | 優先級 |
|-----|------|-------|
| 現有 36 skills 的 SKILL.md 未審查 SDD 對齊 | 如 `sa-analyst`、`sd-architect` 等是否已更新 SDD 工作流程參考 | 🟡 中 |
| 缺少 `sdd-review` skill | 規格文件審查（SCG-4 PR Review 用） | 🟡 建議 |
| 缺少 `scg-report` skill | SCG 閘門狀態報告生成 | 🟡 建議 |

#### 改善行動
- [x] **S-01**: 審查核心 skills（`sa-analyst`, `sd-architect`, `qa-testing`, `ba-analyst`）SKILL.md，確認引用 SDD 工作流程 ✅ 2026-04-15（4 skills 均已 SDD 原生，無需修改）
- [x] **S-02**: 新增 `sdd-review` skill（SCG-4 PR Review 輔助）✅ 2026-04-15（建立 `.claude/skills/sdd-review/SKILL.md`）

---

### 3. Scenarios（🔴 高優先）

#### 現況
- v0.09 `scenarios/` 根目錄有 5 個跨場景指南 + README.md
- SDD v0.01 `scenarios/` 根目錄**完全缺失**這些檔案

#### 缺失檔案

| 缺失檔案 | 功能 | 優先級 |
|---------|------|-------|
| `scenarios/README.md` | 場景選擇說明入口 | 🔴 高 |
| `scenarios/ERROR_RECOVERY_GUIDE.md` | 執行錯誤恢復指南 | 🟡 中 |
| `scenarios/FRONTEND_SPECIFIC_GUIDE.md` | 前端特定指南 | 🟡 中 |
| `scenarios/SCALING_GUIDE.md` | 擴展指南 | 🟡 中 |
| `scenarios/SCENARIO_AGENT_MAPPING.md` | 場景 × Agent 對應表（需更新 SDD 版本） | 🔴 高 |
| `scenarios/SCENARIO_TRANSITION_GUIDE.md` | 場景切換指南 | 🟡 中 |

#### 改善行動
- [x] **SC-01**: 建立 `scenarios/README.md`（SDD 版，含 SCG 閘門說明）✅ 2026-04-15
- [x] **SC-02**: 建立 `scenarios/SCENARIO_AGENT_MAPPING.md`（更新 SDD 10 場景版）✅ 2026-04-15
- [x] **SC-03**: 移植並更新 `ERROR_RECOVERY_GUIDE.md`、`SCALING_GUIDE.md`、`FRONTEND_SPECIFIC_GUIDE.md` ✅ 2026-04-15
- [x] **SC-04**: 移植並更新 `SCENARIO_TRANSITION_GUIDE.md`（新增 SDD 場景轉換規則）✅ 2026-04-15

---

### 4. Workflow

#### 現況
- 兩版本均有 8 core + 13 scenario-specific workflows
- SDD 新增 `sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`

#### 狀態：🟢 結構完整

#### 改善建議
- [x] **W-01**: 驗證 13 個 scenario-specific workflows 內容已整合 SDD SCG 閘門節點 ✅ 2026-04-15（各 workflow 加入 SDD SCG 閘門整合說明節）

---

### 5. Guides

#### 現況
- SDD 指南結構與 v0.09 相同，並新增：
  - `guides/system/sdd/SDD_GUIDE.md`（SDD 快速指引）
  - `guides/user/technical/SMART_DEFAULTS.md`（已在兩版本中）

#### 狀態：🟢 完整（SDD 新增改善）

#### 改善建議
- [x] **G-01**: 驗證 `guides/user/sample/` 下的 21 個場景範例是否需要 SDD 版本更新 ✅ 2026-04-15（21 個指南已加入 SDD v0.01 使用者提示說明）
- [ ] **G-02**: 考慮新增 `guides/user/sample/SDD-{scenario}` 系列範例 — 🟢 低優先，列入 v0.02（需大量撰寫工作，優先級不足）

---

### 6. Prompts（🔴 高優先）

#### 現況
- v0.09 有完整 `prompts/` 目錄：
  - `prompts/complete-flow/`
  - `prompts/quick-start/`
  - `prompts/scenario-prompts/`
- SDD v0.01：**完全沒有 `prompts/` 目錄**

#### 影響
- 使用者無法直接取得各場景的 Prompt 範本
- 降低框架易用性（特別是新手入門）

#### 改善行動
- [x] **P-01**: 建立 `prompts/` 目錄結構（quick-start/, complete-flow/, scenario-prompts/）✅ 2026-04-15
- [x] **P-02**: 移植 v0.09 現有 prompts，更新為 SDD 版本（加入 SCG 閘門步驟）✅ 2026-04-15
- [x] **P-03**: 為 10 個 SDD 場景各撰寫對應的 scenario-prompts ✅ 2026-04-15

---

### 7. Templates

#### 現況
- SDD 大幅擴充 `docs_template/sdd/`（60+ 新模板，正向改善）
- `docs_template/support/` 兩版本相同（完整）

#### 缺失

| 項目 | v0.09 | SDD v0.01 | 處理建議 |
|-----|-------|-----------|---------|
| `docs_template/prd/MVP_Definition_Template.md` | ✅ | ❌ 缺失 | 移植補充 |

#### 改善行動
- [x] **T-01**: 補充 `docs_template/prd/MVP_Definition_Template.md`（SDD 版本，加入 Spec-First 說明）✅ 2026-04-15

---

### 8. Tools

#### 現況
- SDD 新增 `tools/verify_traceability.sh`（正向改善）
- 兩版本均有 `init_project.ps1/sh`、`PROJECT_CLAUDE_Template.md`、`AISDLC_CLAUDE_RULES.md`

#### 缺失

| 項目 | v0.09 | SDD v0.01 | 處理建議 |
|-----|-------|-----------|---------|
| `releases/` 目錄 | ✅ 有（releases/package/, releases/v0.09/） | ❌ 缺失 | 建立（用於框架打包發布） |

#### 改善行動
- [x] **TL-01**: 建立 `releases/` 目錄結構（`releases/backups/`, `releases/v0.01/`）✅ 2026-04-15
- [x] **TL-02**: 評估 `init_project.ps1/sh` 是否已更新為 SDD 版本（加入 SCG 相關初始化）✅ 2026-04-15（兩個腳本均已加入 `--sdd` 旗標，SDD 目錄支援與完成訊息更新）

---

### 9. 版本控管（🔴 高優先）

#### 現況
- v0.09 根目錄有：
  - `AISDLC_UPGRADE_SOP_CheckList.md`（升版前檢查清單）
  - `AISDLC_v0.10_UPGRADE_SOP.md`（升版 SOP）
- SDD v0.01：**完全沒有版本升級文件**

#### 影響
- 未來升版（v0.02 或 v1.0）時，無 SOP 可依循
- 無法確保升版過程不遺漏現有功能

#### 改善行動
- [x] **V-01**: 建立 `AISDLC_SDD_UPGRADE_SOP.md`（SDD 框架升版 SOP）✅ 2026-04-15
- [x] **V-02**: 建立 `AISDLC_SDD_UPGRADE_CHECKLIST.md`（升版前完整檢查清單，含 SDD 閘門驗證）✅ 2026-04-15
- [x] **V-03**: 建立 `SDD_VERSION_HISTORY.md`（版本變更歷程記錄，從 v0.01 開始）✅ 2026-04-15

---

### 10. 目錄結構紀錄

#### 現況
- v0.09: 根目錄有 `DEVELOPMENT_DIRECTORY_STRUCTURE.md`（詳細目錄說明）
- SDD v0.01: 有 `FILE_DIRECTORY_RULES.md`（替代，但側重規則非結構說明）

#### 狀態：🟡 部分覆蓋

#### 改善行動
- [x] **D-01**: 在 `FILE_DIRECTORY_RULES.md` 補充完整的 SDD 目錄樹狀圖（scenarios/ 跨場景指南、prompts/、releases/、版本管理文件）✅ 2026-04-15
- [x] **D-02**: 或另建 `DEVELOPMENT_DIRECTORY_STRUCTURE.md` — 決策：不另建，`FILE_DIRECTORY_RULES.md` 已完整覆蓋 ✅ 2026-04-15

---

## 改善優先級匯總

### 🔴 高優先（立即處理）

| ID | 項目 | 影響範圍 |
|----|------|---------|
| SC-01 | 補充 `scenarios/README.md` | 使用者入口 |
| SC-02 | 補充 `scenarios/SCENARIO_AGENT_MAPPING.md` | Agent 選用指引 |
| P-01~03 | 建立完整 `prompts/` 目錄 | 使用者易用性 |
| V-01~03 | 建立版本控管 SOP + CheckList | 框架可維護性 |

### 🟡 中優先（近期處理）

| ID | 項目 | 影響範圍 |
|----|------|---------|
| A-01~02 | 補充 agent README.md | 框架完整性 |
| SC-03~04 | 移植跨場景指南 | 使用者操作參考 |
| S-01 | 審查核心 skills SDD 對齊 | 技能品質 |
| T-01 | 補充 MVP 模板 | 模板完整性 |
| TL-01~02 | 建立 releases/ + 更新 init scripts | 發布管理 |
| W-01 | 驗證 workflow SDD 整合 | 流程正確性 |
| D-01 | 補充目錄結構視覺化 | 文件完整性 |

### 🟢 低優先（按需處理）

| ID | 項目 | 影響範圍 |
|----|------|---------|
| A-03 | 評估 backup_en 恢復 | 多語支援 |
| S-02 | 新增 sdd-review skill | 功能擴充 |
| G-01~02 | 更新 sample 場景範例 | 示範完整性 |

---

## 工作量估計

| 優先級 | 項目數 | 估計工作量 |
|-------|-------|----------|
| 🔴 高優先 | 10 項 | 1~2 個工作日 |
| 🟡 中優先 | 12 項 | 2~3 個工作日 |
| 🟢 低優先 | 5 項 | 按需 |

---

## Next Actions

建議下一步執行順序：

1. **Phase 08**：補充 `scenarios/` 跨場景指南（SC-01~04）
2. **Phase 09**：建立完整 `prompts/` 目錄（P-01~03）
3. **Phase 10**：建立版本控管文件（V-01~03）
4. **Phase 11**：補充 Agent README + Skills SDD 對齊審查（A-01~02, S-01）
5. **Phase 12**：其餘中低優先項目

---

*報告由 Claude Code 自動生成 | 基於 AISDLC_SDD_v0.01 框架審查*
