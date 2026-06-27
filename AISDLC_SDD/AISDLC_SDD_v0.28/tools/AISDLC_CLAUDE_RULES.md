# AISDLC Claude Rules 配置檔
# AISDLC Claude Code Automated Rules Configuration

> **版本**: v2.0-SDD
> **適用範圍**: AISDLC-SDD v0.01（基於 AISDLC v0.09 升級）
> **最後更新**: 2026-04-17

---

## 🔴 本檔案用途

**本檔案是 AISDLC-SDD 框架的 Claude Code 自動化規則配置檔**，當 Claude Code 載入 `AISDLC_SDD_INIT.md` 時，應自動套用以下所有規則。

**⚠️ CRITICAL**: 這些規則是強制性的，必須在每個使用 AISDLC-SDD 框架的專案中自動執行。

---

## 📋 規則清單

### 1. 溝通語言規範（Communication Language Policy）

**強制規則**:
- ✅ **所有執行過程中的回覆訊息必須使用繁體中文**
- ✅ **所有狀態更新、確認訊息、說明文字必須使用繁體中文**
- ✅ **所有 Todo 任務描述必須使用繁體中文**
- ✅ **專有名詞保持原文**（AISDLC, SDD, Workflow, Agent, SOP, YAML, SCG, ADR, RTM, C4）
- ✅ **文檔標題可中英並列**

**範例**:
```
✅ 正確: 「完成！我已成功修正 3 個檔案」
❌ 錯誤: "Perfect! I have successfully modified 3 files"
```

---

### 2. 文檔目錄規範（Document Directory Standards）

**🛑 強制載入規則（CRITICAL）**:
- 🔴 **每次寫框架檔案前，必須先讀取 `FILE_DIRECTORY_RULES.md`**
- 🔴 **每次寫專案文件前，確認目標路徑在 `docs/` 標準結構內**

**強制規則（SDD v0.01 專案文件目錄）**:
- ✅ **專案文檔必須放置於 `docs/` 目錄**
- ✅ **必須遵循 8 層編號目錄結構**:
  - `docs/01_requirements/` — PRD, FRD, User Stories, Invariant Spec
  - `docs/02_architecture/` — SRD, C4, ADR, As-Is, To-Be
    - `docs/02_architecture/adr/` — Architecture Decision Records
    - `docs/02_architecture/api/` — OpenAPI Spec, Compat 聲明
  - `docs/03_testing/` — RTM, Test Plan, Contract
    - `docs/03_testing/contracts/` — Invariant Test Contract
  - `docs/04_planning/` — Gap Analysis, Refactor Plan
  - `docs/05_development/` — Living Doc Strategy
  - `docs/06_quality/` — Code Quality Baseline, Tech Debt
  - `docs/07_design/` — UI/UX, Database Design
  - `docs/08_deployment/` — CI/CD Pipeline, Release Notes

**驗證命令**:
```bash
for dir in 01_requirements 02_architecture 03_testing 04_planning 05_development 06_quality 07_design 08_deployment; do
  [[ -d "docs/$dir" ]] && echo "✅ docs/$dir/ 存在" || echo "❌ docs/$dir/ 不存在"
done
```

---

### 3. 文檔命名規範（Document Naming Standards）

**強制規則**:
- ✅ **使用 PascalCase 或 Snake_Case**
- ✅ **英文命名，避免中文檔名**
- ✅ **包含文檔類型前綴**（PRD-, FRD-, ADR-, API_, CONTRACT-）

**範例**:
```
✅ 正確:
  - PRD-OrderSystem.md
  - ADR-001-use-postgresql.md
  - API_Order_CreateOrder.md
  - CONTRACT-payment-v1.yaml

❌ 錯誤:
  - 專案需求文檔.md
  - sprint1.md
  - arch.md
```

---

### 4. 寫檔強制檢查（File Write Validation）

**🛑 強制讀取規則（CRITICAL）**:
1. **寫入框架檔案時**: 必須先讀取 `FILE_DIRECTORY_RULES.md`
2. **寫入專案文檔時**: 確認目標目錄符合 Rule 2 規範

**強制規則**:
- 🛑 **每次使用 Write/Edit 工具前必須確認正確目錄**
- ✅ **確認檔案命名格式符合 Rule 3 規範**
- ❌ **絕不寫入工作目錄外**（禁止: /tmp/*, /var/*, 系統目錄）
- ❌ **絕不在框架版本根目錄創建臨時檔案**

**快速規則 - AISDLC 框架 (build/ 目錄)**:
- 📊 分析報告 → `build/reports/analysis/{TOPIC}_{TYPE}.md`
- 📋 階段報告 → `build/reports/phase/{PHASE_NAME}_REPORT.md`
- 📝 計劃文檔 → `build/planning/active/{PLAN_NAME}.md`
- 📦 歸檔計劃 → `build/planning/archive/{PLAN_NAME}.md`

**快速規則 - 使用 AISDLC-SDD 的專案（docs/ 目錄）**:
- 📄 PRD/FRD/Invariant Spec → `docs/01_requirements/`
- 🏗️ SRD/C4/ADR/As-Is/To-Be → `docs/02_architecture/`
- 🔑 ADR 檔案 → `docs/02_architecture/adr/`
- 📡 OpenAPI/Contract/Compat → `docs/02_architecture/api/`
- ✅ RTM/Test Plan/Contract → `docs/03_testing/`
- 🔒 Invariant Test Contract → `docs/03_testing/contracts/`
- 📊 Gap Analysis/Refactor Plan → `docs/04_planning/`
- 🎨 UI/UX/Database Design → `docs/07_design/`
- 🚀 CI/CD/Release Notes → `docs/08_deployment/`

**檢查清單**:
```
□ 已確認檔案類型
□ 已確認正確目錄
□ 已確認命名格式符合規範
□ 確認不是寫入禁止位置
```

---

### 5. 專案初始化標準（Project Initialization Standards）

**強制規則**:
- ✅ **使用 AISDLC-SDD 框架執行任何 workflow 前，必須先讀取 `AISDLC_SDD_INIT.md`**
- ✅ **必須確保標準 docs/ 子目錄結構存在**
- ✅ **必須確保 CLAUDE.md 與 `.claude/skills/` 已部署到目標專案根目錄**

**手動初始化步驟**:
```bash
# 步驟 1: 確認框架目錄
cd /path/to/AISDLC_SDD_v0.01

# 步驟 2: 建立專案文檔目錄（SDD 完整結構）
mkdir -p docs/{01_requirements,02_architecture/adr,02_architecture/api,03_testing/contracts,04_planning,05_development,06_quality,07_design,08_deployment}

# 步驟 3: 確認 .claude/skills/ 已存在（39 個 Claude Code Skills）
ls .claude/skills/ | wc -l   # 應顯示 39
```

**目標專案 CLAUDE.md 設置**:
- 複製 `tools/PROJECT_CLAUDE_Template.md` 到目標專案根目錄並重命名為 `CLAUDE.md`
- 替換模板中的 `{ProjectName}`、`{AISDLC_FRAMEWORK_ROOT}`、`{Scenario}` 佔位符

---

### 6. AISDLC_SDD_INIT.md 載入規範（Init Loading Policy）

**強制規則**:
- ✅ **使用任何 AISDLC-SDD workflow 前，必須先載入 `AISDLC_SDD_INIT.md`**
- ✅ **載入時自動套用本檔案所有 Claude Rules**
- ✅ **自動偵測專案情境並載入對應 Agents**

**載入流程（9 步）**:
```yaml
step_1: 讀取 AISDLC_SDD_INIT.md
step_2: 識別專案情境類型（greenfield / brownfield / refactoring / documentation / devops / migration / integration / testing / performance / security）
step_3: 從「Agent 自動載入配置表」讀取對應情境的配置
step_4: 自動載入 Primary Agents（讀取 YAML 並套用規則）
step_5: 記錄 Supporting Agents 列表（按需載入）
step_6: 載入對應 Workflows + SDD Enhancement
step_7: 確認 .claude/skills/ 已部署（39 個 Claude Code Skills）
step_8: 顯示載入狀態確認
step_9: 開始執行 SOP（含 SDD 閘門）
```

---

### 7. ID 命名規範（ID Naming Convention）

**強制規則**:
- ✅ **遵循 AISDLC-SDD ID 命名規範**

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
| Architecture Decision | `ADR-NNN` | 架構決策記錄（All SDD 場景必用） |

**參考文檔**:
- [AISDLC_ID_Naming_Convention.md](../guides/system/naming/AISDLC_ID_Naming_Convention.md)

---

### 8. 文檔品質標準（Document Quality Standards）

**強制規則**:
- ✅ **所有文檔交付前必須執行品質檢查**
- ✅ **使用 Document_Quality_Checklist.md 進行驗證**

**檢查清單**:
- [ ] 文檔完整性檢查（必填欄位無空白）
- [ ] ID 格式符合 Rule 7 規範
- [ ] 追溯鏈完整（EPIC → US → AC → TC）
- [ ] 技術決策有對應 ADR
- [ ] 文件存放於正確目錄（Rule 2）
- [ ] 可讀性測試通過（15 分鐘測試法）

**參考文檔**:
- [Document_Quality_Checklist.md](../guides/system/quality/Document_Quality_Checklist.md)

---

### 9. 開發-編譯-測試循環強制規則（Development-Build-Test Cycle）

**強制執行原則**: 每完成一支程式（或一個功能單元），**必須立即執行**編譯-測試循環，**絕不累積開發**。

**執行步驟**:
```
開發 1 支程式 → 立即編譯 → 編譯失敗？→ 🔴 立即停止 → 依錯誤修復 → 重新編譯
                ↓
           編譯成功 ✅ → 執行單元測試 → 測試失敗？→ 🔴 立即停止 → 依規格修復 → 重新測試
                                          ↓
                                     測試通過 ✅ → 繼續開發下一支程式
```

**絕對禁止**:
- ❌ 累積開發多支程式後才一次編譯
- ❌ 編譯失敗後繼續開發其他功能
- ❌ 跳過單元測試
- ❌ 測試失敗後「先跳過」（例如：將測試註解掉）

---

### 10. SDD 三大支柱強制規則（SDD Core Pillars）

> **適用範圍**: AISDLC-SDD v0.01 所有場景，強制執行

#### Pillar 1：Spec-First Gate（規格先行）

**SCG 閘門不可跳過**：

| Gate | 時機 | 必要文件 |
|------|------|---------|
| SCG-0 | 需求凍結前 | PRD + FRD 完整性 |
| SCG-1 | 設計凍結前 | SRD + API Spec |
| SCG-2 | 架構凍結前 | C4 圖 + ADR |
| SCG-3 | 開發啟動前 | OpenAPI 3.1 凍結 |
| SCG-4 | PR Review | 實作與規格一致性 |
| SCG-5 | 交付前 | RTM 100% 覆蓋 |
| SCG-6 | 發布前 | 所有閘門通過 |

**❌ 絕對禁止**：未通過 SCG 閘門就進入下一階段。

#### Pillar 2：Design-as-Doc（設計即文件）

- ✅ **每個技術決策必須有對應 ADR**（架構模式、技術棧、整合策略、部署策略）
- ✅ **系統架構必須有 C4 圖**（最少 Context + Container 層）
- ✅ ADR 存放：`docs/02_architecture/adr/ADR-{NNN}-{kebab-title}.md`

#### Pillar 3：Contract-Driven（契約驅動）

- ✅ **OpenAPI 3.1 Contract 在 SCG-3 凍結後，後端實作才可開始**
- ✅ **Consumer-Driven Contract 測試必須在整合前完成**
- ❌ 禁止直接刪除舊有 API 端點（需先建立 API-COMPAT 聲明，設定廢棄期）

**Human 確認點（🔴）**：所有標記 🔴 的 SCG 閘門確認點必須等待人工確認，不可假設通過。

---

### 11. AISDLC-SDD 升版執行規範（Upgrade Execution Policy）

**強制規則** (僅適用於 AISDLC-SDD 框架維護者):
- 🛑 **執行升版前必須先讀取 `AISDLC_SDD_UPGRADE_SOP.md`**
- 🛑 **每完成一個步驟，立即打勾**
- 🛑 **絕對禁止跳過任何步驟**
- 🛑 **升版完成前必須驗證 CheckList 所有項目已打勾**

**參考文檔**:
- [AISDLC_SDD_UPGRADE_SOP.md](../AISDLC_SDD_UPGRADE_SOP.md)
- [AISDLC_SDD_UPGRADE_CHECKLIST.md](../AISDLC_SDD_UPGRADE_CHECKLIST.md)

---

## 🚀 自動化執行流程

### 當 Claude Code 載入 AISDLC_SDD_INIT.md 時，自動執行:

```yaml
step_1: 讀取 AISDLC_SDD_INIT.md
step_2: 自動讀取 tools/AISDLC_CLAUDE_RULES.md（本檔案），套用所有 Rules
step_3: 從「Agent 自動載入配置表」讀取對應情境的配置
step_4: 自動載入 Primary Agents（讀取 YAML 並套用規則）
step_5: 記錄 Supporting Agents 列表（按需載入）
step_6: 載入對應 Workflows + SDD Enhancement
step_7: 確認 .claude/skills/ 已部署（39 個 Claude Code Skills）
step_8: 顯示載入狀態確認（含可用 Skills 列表）
step_9: 開始執行 SOP（含 SDD 閘門）
```

---

## ✅ 規則驗證清單

### 專案啟動時驗證:

```
□ 已套用溝通語言規範（繁體中文）
□ 已讀取 AISDLC_SDD_INIT.md
□ 已確認 docs/ 目錄結構存在（含 adr/、api/、contracts/ 子目錄）
□ 已確認 CLAUDE.md 與 .claude/skills/ 已部署（39 個）
□ 已載入對應專案情境的 Primary Agents
□ 已確認場景對應的 SDD Enhancement 文件
□ 已準備好執行 SCG 閘門驗證
```

### 文檔產出時驗證:

```
□ 檔案命名符合規範（Rule 3）
□ 檔案放置於正確目錄（Rule 2）
□ ID 格式符合規範（Rule 7）
□ 使用繁體中文撰寫（Rule 1）
□ 技術決策有對應 ADR（Rule 10 Pillar 2）
□ 通過文檔品質檢查清單（Rule 8）
□ SCG 閘門狀態確認（Rule 10 Pillar 1）
```

---

## 🔧 規則自訂化（Optional）

目標專案可在 `CLAUDE.md` 中新增專案特定規則：

```markdown
## 專案特定 Claude Rules

### 額外命名規範
- [專案特定的命名規則]

### 額外文檔要求
- [專案特定的文檔要求]

### 禁止事項
- [專案特定的禁止事項]
```

---

## 📚 相關文檔

- [AISDLC_SDD_INIT.md](../AISDLC_SDD_INIT.md) — 框架初始化配置
- [FILE_DIRECTORY_RULES.md](../FILE_DIRECTORY_RULES.md) — 檔案目錄維護規則
- [SDD_Core_Principles.md](../guides/system/sdd/SDD_Core_Principles.md) — SDD 三大支柱詳細說明
- [PROJECT_CLAUDE_Template.md](PROJECT_CLAUDE_Template.md) — 目標專案 CLAUDE.md 模板
- [AISDLC_SDD_UPGRADE_SOP.md](../AISDLC_SDD_UPGRADE_SOP.md) — 框架升版 SOP

---

## 🔄 版本歷史

| 版本 | 日期 | 變更說明 |
|------|------|---------|
| v2.0-SDD | 2026-04-17 | SDD v0.01 全面更新：Rule 2 目錄對齊 SDD 結構、Rule 6 載入流程改為 9 步、Rule 7 補 INV/TD/ADR-NNN、新增 Rule 10 SDD 三大支柱、Skills 數量 33→39、所有 v0.09 路徑更新為 SDD v0.01 |
| v1.1 | 2026-04-11 | 新增 Rule 9 開發-編譯-測試循環；更新自動化流程；Rule 10 升版規範 |
| v1.0 | 2025-01-10 | 初版發布，整合 CLAUDE.md、FILE_DIRECTORY_RULES.md、AISDLC_INIT.md 所有規則 |

---

**文檔元數據**:
- **文檔版本**: v2.0-SDD
- **建立日期**: 2025-01-10
- **最後更新**: 2026-04-17
- **維護者**: AISDLC-SDD Framework Team
- **文檔狀態**: Active
