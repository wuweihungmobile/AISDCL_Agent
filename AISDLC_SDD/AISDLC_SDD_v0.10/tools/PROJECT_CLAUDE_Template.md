# CLAUDE.md
# Claude Code Project Guidance — AISDLC-SDD Framework

**Document Version**: v2.1-SDD
**Last Updated**: 2026-04-17
**AISDLC Version**: v0.01-SDD
**Document Purpose**: 提供 Claude Code 在使用 AISDLC-SDD 框架執行專案時的指導規則

---

> **🔴 Important Notice 🔴**
>
> 此文件為 AISDLC-SDD 框架下的專案 CLAUDE.md 模板。
> 所有指令 **OVERRIDE** Claude Code 預設行為，必須嚴格遵守。
> 使用前請先讀取：`{AISDLC_FRAMEWORK_ROOT}/AISDLC_SDD_INIT.md`

---

## 📋 使用此模板的步驟（Template Setup）

> **複製此模板後，請完成以下替換，再刪除此區塊。**

| 替換項 | 說明 | 範例 |
|--------|------|------|
| `{ProjectName}` | 目標專案名稱 | `OrderManagementSystem` |
| `{AISDLC_FRAMEWORK_ROOT}` | AISDLC-SDD 框架所在的相對或絕對路徑 | `../../AISDLC_SDD_v0.01` 或 `/tools/aisdlc-sdd` |
| `{Scenario}` | 啟動情境代碼 | `greenfield` / `brownfield` / ... |

**完成後刪除此區塊，保留以下所有 Rule。**

---

## 🔴 Rule 1：溝通語言規範（強制）

**CRITICAL: 所有執行過程中的回覆必須使用繁體中文**

| 類型 | 規則 |
|------|------|
| 任務回覆、狀態更新 | ✅ 繁體中文 |
| Todo 任務描述 | ✅ 繁體中文 |
| 文檔標題 | ✅ 可中英並列 |
| 專有名詞 | ✅ 保持原文（AISDLC, SDD, API, PRD, FRD, SRD, ADR, RTM, C4, Git 等） |

```
✅ 正確：「已完成，共修改 3 個檔案」
❌ 錯誤：「Done! I modified 3 files.」
```

---

## 🔴 Rule 2：SDD 三大支柱（強制）

### Spec-First Gate（規格先行）

**規格文件必須在實作前完成並通過 SCG 閘門。**

```
需求規格 → SCG-0 通過 → 設計規格 → SCG-1/2 通過 → Contract 凍結 → SCG-3 通過 → 開始實作
```

❌ **絕對禁止**：未通過 SCG 閘門就開始下一階段。

### Design-as-Doc（設計即文件）

- 每個技術決策必須有對應 ADR（Architecture Decision Record）
- 系統架構必須有 C4 圖（Context / Container / Component）
- ADR 路徑：`docs/02_architecture/adr/ADR-{NNN}-{kebab-title}.md`

### Contract-Driven（契約驅動）

- OpenAPI 3.1 Contract 在 SCG-3 凍結後，後端實作才可開始
- Consumer-Driven Contract 測試必須在整合前完成
- API 規格路徑：`docs/02_architecture/api/`

---

## 🔴 Rule 3：SCG 閘門規則（不可跳過）

| Gate | 名稱 | 時機 | 必要文件 |
|------|------|------|---------|
| SCG-0 | Requirement Spec Gate | 需求凍結前 | PRD + FRD 完整性 |
| SCG-1 | Design Spec Gate | 設計凍結前 | SRD + API Spec |
| SCG-2 | Architecture Review Gate | 架構凍結前 | C4 圖 + ADR |
| SCG-3 | Contract Freeze Gate | 開發啟動前 | OpenAPI 3.1 凍結 |
| SCG-4 | Implementation Compliance Gate | PR Review | 實作與規格一致性 |
| SCG-5 | RTM Completeness Gate | 交付前 | RTM 100% 覆蓋 |
| SCG-6 | Release Readiness Gate | 發布前 | 所有閘門通過 |

**🔴 所有標記 🔴 的確認點必須等待人工確認後才能繼續，不可假設通過！**

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

## 🔴 Rule 5：專案目錄結構

**CRITICAL: 寫入文檔前必須確認正確目錄**

```
{ProjectName}/
├── CLAUDE.md                            # 本指導文件
├── docs/                                # 專案文檔輸出目錄
│   ├── 01_requirements/                 # PRD, FRD, User Stories, Invariant Spec
│   ├── 02_architecture/                 # SRD, C4, ADR, As-Is, To-Be
│   │   ├── adr/                         # ADR 決策記錄
│   │   └── api/                         # API 規格, OpenAPI Spec, Compat 聲明
│   ├── 03_testing/                      # RTM, Test Plan, Contract
│   │   └── contracts/                   # Invariant Test Contract
│   ├── 04_planning/                     # Gap Analysis, Refactor Plan
│   ├── 05_development/                  # Living Doc Strategy
│   ├── 06_quality/                      # Code Quality Baseline, Tech Debt
│   ├── 07_design/                       # UI/UX, Database Design
│   └── 08_deployment/                   # CI/CD Pipeline, Release Notes
```

### 文件路徑快速對照

| 文件類型 | 正確路徑 |
|---------|---------|
| PRD / FRD / Invariant Spec | `docs/01_requirements/` |
| SRD / C4 / ADR / As-Is / To-Be | `docs/02_architecture/` |
| ADR 檔案 | `docs/02_architecture/adr/` |
| API 規格 / Compat 聲明 | `docs/02_architecture/api/` |
| RTM / Test Plan / Contract | `docs/03_testing/` |
| Invariant Test Contract | `docs/03_testing/contracts/` |
| Gap Analysis / Refactor Plan | `docs/04_planning/` |
| Living Doc Strategy | `docs/05_development/` |
| Code Quality Baseline / Tech Debt | `docs/06_quality/` |
| UI/UX / Database Design | `docs/07_design/` |
| CI/CD Pipeline / Release Notes | `docs/08_deployment/` |

**❌ 絕對禁止**：寫入 `/tmp/`、`/var/`、系統目錄或框架模板目錄。

---

## 🔴 Rule 6：檔案命名規範

| 類型 | 格式 | 範例 |
|------|------|------|
| 需求文件 | `{TYPE}-{SystemName}.md` | `PRD-OrderSystem.md` |
| ADR | `ADR-{NNN}-{kebab-title}.md` | `ADR-001-use-postgresql.md` |
| API 規格 | `API_{Module}_{Endpoint}.md` | `API_Order_CreateOrder.md` |
| API Compat | `API-COMPAT-{Module}.md` | `API-COMPAT-Payment.md` |
| 測試合約 | `INVARIANT-CONTRACT-{Module}.md` | `INVARIANT-CONTRACT-Order.md` |

**❌ 禁止**：中文檔名、縮寫不明命名（`arch.md`、`sprint1.md`）。

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
| Architecture Decision | `ADR-NNN` | 架構決策記錄 |

---

## 🤖 Rule 8：Agent 使用規則

**CRITICAL: 執行任務時，必須自動載入並扮演對應 Agent 角色**

### 核心 Agent 列表

| Agent | 角色 | SDD 技能 | 使用時機 / SCG |
|-------|------|---------|--------------|
| `04.sa-analyst-zh.yaml` | SA 分析師 | 逆向規格工程、Gap Analysis、Invariants 提取 | 需求分析 / SCG-0 |
| `05.sd-architect-zh.yaml` | SD 架構師 | As-Is C4、ADR Archaeology、Before/After 比較 | 架構設計 / SCG-1~2 |
| `06.dev-developer-zh.yaml` | 開發者 | Contract 驗證、規格合規 | 程式碼實作 / SCG-4 |
| `07.qa-tester-zh.yaml` | QA 測試師 | As-Is 測試規格、Invariant Test Contract | 測試 / SCG-5 |
| `03.pm-po-agent-zh.yaml` | 產品經理 | PRD 管理、Sprint 規劃 | 需求優先級 |
| `02.ba-business-analyst-zh.yaml` | 業務分析師 | 業務邏輯驗證 | 業務規則確認 |

### Agent 載入流程

```yaml
step_1: 讀取 {AISDLC_FRAMEWORK_ROOT}/AISDLC_SDD_INIT.md 的 auto_load_config
step_2: 識別場景（greenfield/brownfield/refactoring/...）
step_3: 自動載入 Primary Agents
step_4: 依需求載入 Supporting Agents
step_5: 按 Agent 規範執行任務
```

### 場景對應

| 場景 | 必讀 Enhancement |
|------|-----------------|
| greenfield | `{AISDLC_FRAMEWORK_ROOT}/scenarios/greenfield/SDD_GREENFIELD_ENHANCEMENT.md` |
| brownfield | `{AISDLC_FRAMEWORK_ROOT}/scenarios/brownfield/SDD_BROWNFIELD_ENHANCEMENT.md` |
| refactoring | `{AISDLC_FRAMEWORK_ROOT}/scenarios/refactoring/SDD_REFACTORING_ENHANCEMENT.md` |
| documentation | `{AISDLC_FRAMEWORK_ROOT}/scenarios/documentation/SDD_DOCUMENTATION_ENHANCEMENT.md` |
| devops | `{AISDLC_FRAMEWORK_ROOT}/scenarios/devops/SDD_DEVOPS_ENHANCEMENT.md` |
| integration | `{AISDLC_FRAMEWORK_ROOT}/scenarios/integration/SDD_INTEGRATION_ENHANCEMENT.md` |
| migration | `{AISDLC_FRAMEWORK_ROOT}/scenarios/migration/SDD_MIGRATION_ENHANCEMENT.md` |
| performance | `{AISDLC_FRAMEWORK_ROOT}/scenarios/performance/SDD_PERFORMANCE_ENHANCEMENT.md` |
| security | `{AISDLC_FRAMEWORK_ROOT}/scenarios/security/SDD_SECURITY_ENHANCEMENT.md` |
| testing | `{AISDLC_FRAMEWORK_ROOT}/scenarios/testing/SDD_TESTING_ENHANCEMENT.md` |

---

## 📋 Rule 9：文檔品質標準

所有規格文件交付前必須執行自我檢查：

- [ ] 必填欄位完整（無空白佔位符）
- [ ] 追溯鏈完整（EPIC → US → AC → TC）
- [ ] 技術決策有對應 ADR
- [ ] ID 格式符合 Rule 7 規範
- [ ] 文件存放於正確目錄（Rule 5）
- [ ] 規格先於實作（未開始 coding 前 SCG 已通過）

---

## 🔗 框架參考文件

| 文件 | 路徑 | 用途 |
|------|------|------|
| 框架入口 | `{AISDLC_FRAMEWORK_ROOT}/AISDLC_SDD_INIT.md` | **使用框架前必讀** |
| SDD 核心原則 | `{AISDLC_FRAMEWORK_ROOT}/guides/system/sdd/SDD_Core_Principles.md` | 三大支柱詳細說明 |
| 目錄規則 | `{AISDLC_FRAMEWORK_ROOT}/FILE_DIRECTORY_RULES.md` | 寫檔前查閱 |
| SCG 閘門執行 | `{AISDLC_FRAMEWORK_ROOT}/workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md` | 閘門驗證程序 |
| SDD 快速指引 | `{AISDLC_FRAMEWORK_ROOT}/guides/system/sdd/SDD_GUIDE.md` | 快速上手 |
| Claude 規則 | `{AISDLC_FRAMEWORK_ROOT}/tools/AISDLC_CLAUDE_RULES.md` | 詳細規則參考 |

---

## ⚠️ DO / DO NOT

### ✅ DO:
- 使用繁體中文回覆（專有名詞除外）
- 規格文件完成並通過 SCG 閘門後才進入下一階段
- 每個技術決策建立對應 ADR
- OpenAPI Contract 凍結後才開始後端實作
- 每支程式開發完立即編譯測試
- 文檔寫入前確認正確目錄
- 遵循 AISDLC ID 命名規範
- SCG 閘門確認點等待人工確認

### ❌ DO NOT:
- 使用英文回覆訊息（專有名詞除外）
- 跳過 SCG 閘門直接開發
- 先寫程式再補文件
- 設計文件凍結前實作 API
- 直接刪除舊有 API 端點（需先建立 API-COMPAT 聲明）
- 累積開發多支程式後才編譯
- 編譯失敗或測試失敗後繼續開發
- 文檔寫入錯誤目錄
- 效能測試前未定義 SLO
- 安全實作前未做 STRIDE 威脅建模

---

## 🚀 快速啟動

```
AISDLC {Scenario} {專案簡述}
範例：AISDLC greenfield 電商訂單管理系統
```

情境代碼：`greenfield` | `brownfield` | `refactoring` | `migration` | `performance` | `integration` | `devops` | `testing` | `documentation` | `security`

---

**文檔元數據**:
- **文檔版本**: v2.1-SDD
- **建立日期**: 2026-04-16
- **最後更新**: 2026-04-17
- **適用 AISDLC 版本**: v0.01-SDD
- **維護者**: AISDLC-SDD Framework Team
- **文檔狀態**: Active
