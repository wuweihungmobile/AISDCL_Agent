# 文件品質檢查清單
# Document Quality Checklist

**文檔版本**: v1.0
**建立日期**: 2025-11-14
**適用範圍**: AISDLC Framework 所有文檔
**AISDLC 版本**: v0.01

---

## 📋 文檔目的

本文檔提供 **AISDLC 專案文檔品質檢查標準**，確保所有文檔不僅完整，而且易讀、一致、可維護。

### 為什麼需要文件品質檢查？

1. **提升可讀性**: 確保團隊成員能快速理解文檔內容
2. **減少溝通成本**: 避免因文檔不清楚而產生的反覆溝通
3. **保證一致性**: 所有文檔使用統一的格式和術語
4. **易於維護**: 清晰的結構便於後續更新和維護

---

## 📊 文件品質檢查分類

本檢查清單分為 **4 大類別**：

1. **文件完整性檢查** - 確保所有必要文件已產出
2. **文件品質檢查** - 確保文件易讀、清晰、一致
3. **文件可讀性測試** - 實際測試文件是否易於理解
4. **技術文檔專項檢查** - API、Architecture 等技術文檔的特殊檢查

---

## ✅ 1. 文件完整性檢查

### 1.1 需求階段文檔（階段 2-4）

- [ ] **PRD** (Product Requirements Document)
  - 檔名格式: `PRD_[ProjectName]_v1.0.md`
  - 使用模板: [PRD_Universal_Template.md](../docs_template/core/prd/PRD_Universal_Template.md)
  - 包含: Feature ID (F-XXX), NFR ID (NFR-XXX)

- [ ] **FRD** (Functional Requirements Document)
  - 檔名格式: `FRD_[ProjectName]_v1.0.md`
  - 使用模板: [FRD_Universal_Template.md](../docs_template/core/frd/FRD_Universal_Template.md)
  - 包含: Business Rule ID (BR-XXX), User Role ID (UR-XXX)

- [ ] **需求提取報告** (Requirement Extraction Report)
  - 檔名格式: `Requirement_Extraction_Report_[ProjectName].md`
  - 使用模板: [Requirement_Extraction_Report_Template.md](../docs_template/support/Requirement_Extraction_Report_Template.md)

- [ ] **人機協作記錄** (Collaboration Log)
  - 檔名格式: `Collaboration_Log_[ProjectName].md`
  - 使用模板: [Collaboration_Log_Template.md](../docs_template/support/Collaboration_Log_Template.md)

- [ ] **MVP 定義** (若需要)
  - 檔名格式: `MVP_Definition_[ProjectName].md`
  - 使用模板: [MVP_Definition_Template.md](../docs_template/prd/MVP_Definition_Template.md)

### 1.2 設計階段文檔（階段 5）

- [ ] **SRD** (System Requirements Document)
  - 檔名格式: `SRD_[ProjectName]_v1.0.md`
  - 使用模板: [SRD_Universal_Template.md](../docs_template/core/srd/SRD_Universal_Template.md)

- [ ] **Architecture Documents**
  - C4 Model 圖表 (Level 1-2 必須，Level 3-4 依專案規模)
  - 資料庫設計 (ER 圖或 Object Model Schema)
  - 部署架構圖

- [ ] **API Specifications** (如有 Backend API)
  - 每個 API 端點一份規格文件: `API_[Module]_[Endpoint].md`
  - API 索引文件: `API_Index.md`
  - 使用模板: [API_Specification_Template.md](../docs_template/srd/api/API_Specification_Template.md)

- [ ] **資料訪問層設計** (如無 Backend API)
  - 使用模板: [Data_Access_Layer_Template.md](../docs_template/srd/Data_Access_Layer_Template.md)

- [ ] **技術選型報告**
  - 檔名格式: `Tech_Stack_Selection_Report_[ProjectName].md`
  - 使用模板: [Tech_Stack_Selection_Report_Template.md](../docs_template/support/Tech_Stack_Selection_Report_Template.md)

### 1.3 開發階段文檔（階段 6-8）

- [ ] **User Stories**
  - 檔名格式: `User_Stories_[EpicName].md`
  - 使用模板: [User_Story_Template.md](../docs_template/core/prd/User_Story_Template.md)
  - 包含: Epic ID (EPIC-XXX), User Story ID (US-XXX), AC ID (AC-XXX-Y)

- [ ] **Sprint Plan**
  - 每個 Sprint 一份計畫: `Sprint_[X]_Plan.md`
  - 包含: Sprint 目標、User Stories、時程、風險

- [ ] **開發指引** (Developer Guidelines)
  - Coding Standards
  - Git Workflow
  - PR/Code Review 流程
  - 環境建置指南

### 1.4 測試與交付文檔（階段 9）

- [ ] **Test Cases**
  - 測試案例文件: `TestCase_[Module].md`
  - Test Case ID (TC-XXX-Y-Z) 對應 AC ID

- [ ] **Test Reports**
  - 測試報告: `Test_Report_Sprint_[X].md`

- [ ] **Deployment Guide**
  - 部署指南: `Deployment_Guide.md`

---

## ✅ 2. 文件品質檢查

### 2.1 可讀性檢查

#### 2.1.1 術語與縮寫說明

- [ ] **所有專有名詞首次出現時有定義或解釋**
  - ✅ 正確範例: 「PRD (Product Requirements Document) 是產品需求文件」
  - ❌ 錯誤範例: 直接使用 「PRD」 而無說明

- [ ] **所有縮寫有完整形式說明**
  - 常見縮寫檢查清單:
    - [ ] PRD (Product Requirements Document)
    - [ ] FRD (Functional Requirements Document)
    - [ ] SRD (System Requirements Document)
    - [ ] RICE (Reach, Impact, Confidence, Effort)
    - [ ] MVP (Minimum Viable Product)
    - [ ] AC (Acceptance Criteria)
    - [ ] API (Application Programming Interface)

- [ ] **技術術語使用一致**
  - ✅ 正確: 全文統一使用「交易」
  - ❌ 錯誤: 混用「交易」、「記錄」、「transaction」

#### 2.1.2 文檔結構檢查

- [ ] **章節編號一致**
  - 使用標準 Markdown 格式: `#`, `##`, `###`
  - 確保編號連續，不跳級

- [ ] **標題層級正確**
  - ✅ 正確: `# H1` → `## H2` → `### H3`
  - ❌ 錯誤: `# H1` → `### H3` (跳過 H2)

- [ ] **段落長度適中**
  - 每段不超過 5-7 行
  - 使用子標題分隔長內容

- [ ] **列表格式一致**
  - 統一使用 `-` 或 `*` 作為無序列表符號
  - 有序列表使用 `1.`, `2.`, `3.`

#### 2.1.3 語言與表達

- [ ] **語言簡潔明確**
  - 避免冗長句子
  - 使用主動語態

- [ ] **避免模糊用詞**
  - ❌ 避免: 「可能」、「大概」、「差不多」
  - ✅ 使用: 「必須」、「應該」、「預計」

- [ ] **專業性與親和力平衡**
  - 使用專業術語，但加上解釋
  - 避免過於口語化或過於學術化

### 2.2 視覺元素檢查

#### 2.2.1 圖表品質

- [ ] **所有圖表清晰可讀**
  - 解析度足夠（建議 ≥ 1024px 寬度）
  - 文字大小適中（≥ 10pt）
  - 顏色對比度足夠

- [ ] **圖表有標題和說明**
  - 每個圖表上方有標題
  - 複雜圖表有說明文字

- [ ] **流程圖規範**
  - [ ] 箭頭方向正確
  - [ ] 起點和終點清楚
  - [ ] 決策點使用菱形
  - [ ] 流程框使用矩形

#### 2.2.2 程式碼範例

- [ ] **程式碼區塊使用語法高亮**
  - 使用正確的語言標記: ` ```javascript`, ` ```python`, ` ```yaml`

- [ ] **程式碼範例完整可執行**
  - 避免省略重要部分
  - 提供必要的 import/require

- [ ] **程式碼有註解說明**
  - 複雜邏輯加上註解
  - 範例程式碼說明用途

### 2.3 連結與參照檢查

#### 2.3.1 內部連結

- [ ] **文件間交叉連結正確**
  - 檢查所有 `[文字](路徑)` 格式的連結
  - 確保無 404 錯誤

- [ ] **相對路徑正確**
  - 使用相對路徑而非絕對路徑
  - 範例: `../../docs_template/core/prd/PRD_Universal_Template.md`

- [ ] **錨點連結正確**
  - 範例: `[功能需求](#功能需求)`
  - 確保章節標題存在

#### 2.3.2 外部連結

- [ ] **外部連結有效**
  - 檢查所有 HTTP/HTTPS 連結
  - 確保連結未失效

- [ ] **外部連結使用說明**
  - 說明連結指向的內容
  - 範例: 「詳見 [C4 Model 官方文件](https://c4model.com/)」

### 2.4 一致性檢查

#### 2.4.1 ID 命名一致性

- [ ] **所有 ID 遵循統一規範**
  - 參考: [AISDLC_ID_Naming_Convention.md](AISDLC_ID_Naming_Convention.md)
  - 檢查清單:
    - [ ] Feature ID: F-XXX (3 位數)
    - [ ] NFR ID: NFR-XXX
    - [ ] Business Rule ID: BR-XXX
    - [ ] Epic ID: EPIC-XXX
    - [ ] User Story ID: US-XXX
    - [ ] AC ID: AC-XXX-Y
    - [ ] API ID: API-XXX
    - [ ] Test Case ID: TC-XXX-Y-Z

- [ ] **ID 編號連續，無跳號**
  - ✅ 正確: F-001, F-002, F-003
  - ❌ 錯誤: F-001, F-003, F-005

#### 2.4.2 日期與時間格式

- [ ] **日期格式統一使用 YYYY-MM-DD**
  - ✅ 正確: 2025-11-14
  - ❌ 錯誤: 14/11/2025, 11-14-2025

- [ ] **時間格式統一**
  - 使用 24 小時制: 14:30
  - 或明確標註 AM/PM: 2:30 PM

#### 2.4.3 版本號管理

- [ ] **版本號格式一致**
  - 使用 Semantic Versioning: vX.Y.Z
  - 範例: v1.0.0, v1.1.0, v2.0.0

- [ ] **變更記錄完整**
  - 每次版本更新記錄在 Change Log
  - 說明變更原因和內容

---

## ✅ 3. 文件可讀性測試

### 3.1 測試方法

**目的**: 驗證文件是否易於理解，非專案成員能否快速掌握核心內容

**測試流程**:
1. 找一位 **非專案成員**（開發者、QA、PM 皆可）
2. 請其閱讀文件 **15 分鐘**
3. 詢問以下問題，確認理解程度

### 3.2 通過標準：能回答以下問題

#### 3.2.1 專案概述（PRD / Project README）

- [ ] **這個專案要做什麼？**
  - 能用一句話描述專案目標
  - 能說出目標使用者是誰

- [ ] **為什麼要做這個專案？**
  - 理解專案的商業價值
  - 理解要解決的問題

#### 3.2.2 功能需求（PRD / FRD）

- [ ] **主要功能有哪些？**
  - 能列出 3-5 個核心功能
  - 理解 MVP 範圍（若有）

- [ ] **功能的優先級是什麼？**
  - 理解哪些是 Must-have，哪些是 Nice-to-have

#### 3.2.3 技術架構（SRD）

- [ ] **技術架構是什麼？**
  - 理解系統整體架構（Frontend, Backend, Database）
  - 理解資料流向

- [ ] **使用了哪些技術棧？**
  - 能列出主要技術（如 React Native, Node.js, MongoDB）

#### 3.2.4 開發計畫（Sprint Plan）

- [ ] **Sprint 1 要完成什麼？**
  - 理解第一個 Sprint 的目標
  - 能列出主要的 User Stories

- [ ] **整體時程規劃是什麼？**
  - 理解專案預計週期
  - 理解主要里程碑

### 3.3 測試結果評估

| 答對問題數 | 評級 | 建議 |
|----------|------|------|
| 7-8 題 | ✅ 優秀 | 文件可讀性良好 |
| 5-6 題 | ⚠️ 及格 | 建議優化部分章節 |
| < 5 題 | ❌ 不及格 | 需大幅改善文件結構和說明 |

### 3.4 改善建議（針對不及格文件）

如果測試不及格，檢查以下常見問題：

- [ ] **缺少專案概述章節**
  - 新增「Executive Summary」或「專案概述」

- [ ] **術語過多，缺少解釋**
  - 新增「術語表 (Glossary)」章節
  - 首次出現時加上解釋

- [ ] **結構混亂，章節跳躍**
  - 重新整理章節順序
  - 確保邏輯流暢（從概述 → 需求 → 設計 → 實作）

- [ ] **圖表過少，文字過多**
  - 新增流程圖、架構圖
  - 使用表格整理資訊

---

## ✅ 4. 技術文檔專項檢查

### 4.1 API Specification 檢查

- [ ] **每個 API 端點有獨立規格文件**
  - 檔名格式: `API_[Module]_[Endpoint].md`
  - 範例: `API_Transaction_CreateTransaction.md`

- [ ] **API 規格包含必要資訊**
  - [ ] API ID (API-XXX)
  - [ ] HTTP Method (GET/POST/PUT/DELETE)
  - [ ] Endpoint URL
  - [ ] Request Parameters (含類型、必填/選填、範例)
  - [ ] Request Body Schema (JSON Schema)
  - [ ] Response Schema (含 Success/Error)
  - [ ] 錯誤代碼說明 (Error Codes)
  - [ ] 使用範例 (Example)

- [ ] **API 索引文件完整**
  - 列出所有 API 端點
  - 提供快速查詢連結

### 4.2 Architecture Documents 檢查

- [ ] **C4 Model 圖表層級正確**
  - 參考: [C4_Model_Guidelines.md](C4_Model_Guidelines.md)
  - 檢查清單:
    - [ ] Level 1: System Context Diagram（所有專案必須）
    - [ ] Level 2: Container Diagram（所有專案必須）
    - [ ] Level 3: Component Diagram（中大型專案必須）
    - [ ] Level 4: Code Diagram（選用）

- [ ] **資料庫設計文件完整**
  - 關聯式資料庫: ER 圖
  - Object Database: Object Model Schema
  - 包含所有 Table/Collection 定義
  - 包含 Relationships 說明

- [ ] **部署架構圖清晰**
  - 標示所有環境（Development, Staging, Production）
  - 標示所有服務（Frontend, Backend, Database, Cache）
  - 標示網路拓樸（Load Balancer, CDN, Firewall）

### 4.3 User Story 檢查

- [ ] **User Story 格式正確**
  - 使用標準格式: 「作為一個 [角色]，我想要 [功能]，以便於 [價值]」

- [ ] **Acceptance Criteria 使用 Given-When-Then 格式**
  - Given [前提條件]
  - When [操作行為]
  - Then [預期結果]

- [ ] **Story Points 已估算**
  - 參考: [Estimation_Standards.md](Estimation_Standards.md)
  - 使用 Planning Poker 或基準對比法

- [ ] **追蹤鏈完整**
  - Feature → Epic → User Story → AC → Test Case

---

## 📋 完整檢查清單（一頁總結）

### 快速檢查版（10 分鐘）

| 類別 | 檢查項目 | 通過 |
|-----|---------|------|
| **完整性** | PRD、FRD、SRD、API Spec、User Stories 已產出 | ☐ |
| **可讀性** | 術語有解釋、章節層級正確、段落適中 | ☐ |
| **視覺** | 圖表清晰、程式碼有高亮、流程圖正確 | ☐ |
| **連結** | 內部連結正確、外部連結有效 | ☐ |
| **一致性** | ID 格式統一、日期格式統一、術語一致 | ☐ |
| **測試** | 非專案成員能在 15 分鐘內理解核心內容 | ☐ |

### 詳細檢查版（1 小時）

使用本文檔的完整檢查清單，逐項檢查所有文檔品質。

---

## 🔄 文件品質改善流程

### 流程圖

```
文件產出
    ↓
執行文件完整性檢查
    ↓
執行文件品質檢查
    ↓
執行可讀性測試
    ↓
[是否通過？]
    ↓ 是
文件品質合格，可交付
    ↓ 否
識別問題並改善
    ↓
重新檢查
```

### 改善優先級

| 優先級 | 問題類型 | 影響 | 處理時間 |
|-------|---------|------|---------|
| **P0** | 文件缺失、連結失效 | 嚴重影響使用 | 立即修正 |
| **P1** | 術語不一致、ID 格式錯誤 | 影響理解和追蹤 | 1-2 天 |
| **P2** | 圖表品質、格式美化 | 影響閱讀體驗 | 1 週 |

---

## 🛠️ 工具推薦

### 文件品質檢查工具

| 工具 | 用途 | 備註 |
|-----|------|------|
| **Markdown Lint** | Markdown 格式檢查 | VS Code Extension |
| **markdownlint-cli** | 命令列格式檢查 | 可整合 CI/CD |
| **markdown-link-check** | 檢查連結有效性 | npm package |
| **Vale** | 文件風格檢查 | 可自訂規則 |
| **Grammarly** | 英文語法檢查 | 線上工具 |

### 圖表工具

| 工具 | 用途 | 備註 |
|-----|------|------|
| **Draw.io** | 流程圖、架構圖 | 免費，支援 VSCode Extension |
| **PlantUML** | 程式碼生成圖表 | 適合 C4 Model |
| **Mermaid** | Markdown 內嵌圖表 | GitHub 原生支援 |
| **Excalidraw** | 手繪風格圖表 | 適合快速草稿 |

---

## 📖 MoneyTracker 範例

### 範例：PRD 文件品質檢查

**檢查項目**:

✅ **通過範例**:
```markdown
# PRD_MoneyTracker_v1.0

## 1. 專案概述

MoneyTracker 是一款 **個人記帳 Mobile App**，幫助使用者快速記錄日常收支，並提供統計分析功能。

**目標使用者**: 25-45 歲，需要簡單易用的記帳工具

**核心價值**: 讓記帳變得簡單、快速，不需要複雜操作

## 2. 功能需求

### F-001: 快速記帳
使用者可以在 3 秒內完成一筆記帳記錄。

**優先級**: Must-have (P0)
**RICE 分數**: 850
...
```

**通過原因**:
- ✅ 專有名詞「Mobile App」清楚說明
- ✅ 目標使用者明確
- ✅ 核心價值簡潔易懂
- ✅ Feature ID 格式正確 (F-001)
- ✅ 優先級清楚標示

---

❌ **不通過範例**:
```markdown
# PRD

## 需求
- 記帳功能
- 統計功能
- 其他功能
```

**不通過原因**:
- ❌ 缺少專案概述
- ❌ 缺少目標使用者說明
- ❌ 功能描述過於簡略
- ❌ 沒有使用 Feature ID
- ❌ 沒有優先級

---

## 🔗 相關文件

- [AISDLC_ID_Naming_Convention.md](AISDLC_ID_Naming_Convention.md) - ID 命名規範
- [Estimation_Standards.md](Estimation_Standards.md) - 估算標準
- [C4_Model_Guidelines.md](C4_Model_Guidelines.md) - C4 Model 層級要求
- [Greenfield SOP.md](../scenarios/greenfield/SOP.md) - 階段 9 步驟 9.1 文件檢查

---

## 🔄 版本歷史

| 版本 | 日期 | 變更說明 |
|-----|------|---------|
| v1.0 | 2025-11-14 | 初版建立 - Phase 3 P2 問題修正 (#26) |

---

**文檔維護者**: AISDLC Framework Team
**最後更新**: 2025-11-14
**狀態**: ✅ Active

---

**End of Document**
