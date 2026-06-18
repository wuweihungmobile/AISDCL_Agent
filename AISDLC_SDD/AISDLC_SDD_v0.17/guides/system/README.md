# guides/system/ - 系統參考文件目錄
# System Reference Documents Directory

> **🤖 AI Agent 專用參考文件**
>
> 本目錄包含給 **AI Agent** 使用的技術規範、標準和指引文件。
> 這些文件會被 Agent 載入並執行，包含具體的規則、格式和流程定義。

---

**版本**: v0.01
**最後更新**: 2026-04-11
**維護者**: AISDLC Framework Team
**適用範圍**: AISDLC-SDD v0.01+

---

## 📋 目錄說明

### 用途定位

**system/** 目錄用於存放：
- ✅ **結構化、標準化的內容** - 包含具體的規則、格式、流程定義
- ✅ **給 AI Agent 使用的技術規範** - 會被 Agent 載入並執行
- ✅ **系統級的標準和指引** - ID 命名、架構設計、API 規範等

**不應放在此目錄**:
- ❌ 給人類閱讀的教學文件 → 應放在 `guides/user/onboarding/`
- ❌ 流程操作指南 → 應放在 `guides/user/process/`
- ❌ 使用者快速上手指南 → 應放在 `guides/user/onboarding/`

---

## 📁 子目錄結構

### 🔤 naming/ - 命名與識別規範
**用途**: ID、變數、檔案命名規範

**檔案清單**:
- [AISDLC_ID_Naming_Convention.md](naming/AISDLC_ID_Naming_Convention.md) - 統一 ID 命名規範（F-XXX, US-XXX, AC-XXX-Y 等）

**使用時機**: 需求分析、User Story 撰寫、測試案例編號

---

### 🏗️ architecture/ - 架構設計規範
**用途**: 系統架構設計、C4 模型、架構圖維護

**檔案清單**:
- [C4_Model_Guidelines.md](architecture/C4_Model_Guidelines.md) - C4 架構設計指南
- [Architecture_Diagram_Maintenance.md](architecture/Architecture_Diagram_Maintenance.md) - 架構圖版本控制指引
- [Web_Architecture_Decision_Tree.md](architecture/Web_Architecture_Decision_Tree.md) - Web 架構決策樹
- [Observability_Design_Guide.md](architecture/Observability_Design_Guide.md) - 可觀測性設計指南（Logging, Metrics, Tracing）
- [High_Availability_Architecture_Checklist.md](architecture/High_Availability_Architecture_Checklist.md) - 高可用架構設計檢查清單
- [Security_Architecture_Checklist.md](architecture/Security_Architecture_Checklist.md) - 安全架構設計檢查清單

**使用時機**: Greenfield SOP Stage 5（SRD 撰寫）、技術選型階段、安全與 HA 架構審查

---

### 🔌 api/ - API 設計規範
**用途**: API 版本管理、API 規範定義

**檔案清單**:
- [API_Versioning_Guide.md](api/API_Versioning_Guide.md) - API 版本升級與管理指引
- [API_Mandatory_Checklist.md](api/API_Mandatory_Checklist.md) - API 設計強制檢查清單（認證、錯誤格式、文檔）

**使用時機**: API 設計階段、API 版本升級時、API 設計審查

---

### ✅ testing/ - 測試規範
**用途**: 測試策略、AT vs TC 區分

**檔案清單**:
- [AT_vs_TC_Guide.md](testing/AT_vs_TC_Guide.md) - Acceptance Test vs Test Case 區分指引
- [Performance_Test_Plan_Template.md](testing/Performance_Test_Plan_Template.md) - 效能測試計畫模板（負載測試、壓力測試規範）

**使用時機**:
- AT_vs_TC_Guide - 測試階段、User Story 撰寫 AC 時
- Performance_Test_Plan_Template - Performance 情境、SRD 非功能需求撰寫

---

### 🔍 quality/ - 品質管理規範
**用途**: 文件品質、安全檢查、Code Review

**檔案清單**:
- [Document_Quality_Checklist.md](quality/Document_Quality_Checklist.md) - 文件品質檢查清單
- [Security_Design_Checklist.md](quality/Security_Design_Checklist.md) - 安全設計檢查清單
- [Security_Threat_Modeling_Guide.md](quality/Security_Threat_Modeling_Guide.md) - 安全威脅建模指南（STRIDE 方法論）

**使用時機**:
- Document_Quality_Checklist - Greenfield SOP Stage 9（文件品質檢查）
- Security_Design_Checklist - Greenfield SOP Stage 5（SRD 撰寫）
- Security_Threat_Modeling_Guide - Security 情境、SRD 安全章節撰寫

---

### 📊 planning/ - 規劃與估算規範
**用途**: 估算標準、Kano 模型、優先級排序

**檔案清單**:
- [Estimation_Standards.md](planning/Estimation_Standards.md) - 估算標準化指南（Story Points, Velocity, RICE）
- [Kano_Model_Guide.md](planning/Kano_Model_Guide.md) - Kano 模型功能分類指引
- [Tech_Stack_Selection_Matrix.md](planning/Tech_Stack_Selection_Matrix.md) - 技術棧選型評估矩陣

**使用時機**:
- Estimation_Standards - 規劃階段、Sprint Planning
- Kano_Model_Guide - Greenfield SOP Stage 4 步驟 4.2（MVP 範圍界定）
- Tech_Stack_Selection_Matrix - 技術選型階段、Migration 情境評估

---

### 🤖 agent/ - Agent 管理規範
**用途**: Agent 選擇、協作模式

**檔案清單**:
- [Platform_Agent_Selection_Guide.md](agent/Platform_Agent_Selection_Guide.md) - 跨平台 Agent 選擇指南
- [Specialized_Agent_Selection_Guide.md](agent/Specialized_Agent_Selection_Guide.md) - Specialized Agent 選擇指南

**使用時機**:
- Platform_Agent_Selection_Guide - 技術選型階段
- Specialized_Agent_Selection_Guide - Agent 載入時（AI 系統自動參考）

---

## 🔄 維護規則

### 新增檔案時

當需要新增系統參考文件時，請遵循以下決策流程：

```
問題：這個檔案是什麼類型的規範？
│
├─ 命名規範（ID、變數、檔案命名） → naming/
├─ 架構設計（C4、架構圖、可觀測性） → architecture/
├─ API 設計（API 版本、API 規範） → api/
├─ 測試規範（AT vs TC、測試策略） → testing/
├─ 品質管理（文件品質、安全檢查） → quality/
├─ 規劃估算（Story Points、Kano、RICE） → planning/
└─ Agent 管理（Agent 選擇、協作模式） → agent/
```

### 檔案命名規範

- ✅ 使用名詞 + 動詞組合: `API_Versioning_Guide.md`
- ✅ 明確說明用途: `AT_vs_TC_Guide.md`
- ✅ 包含領域關鍵字: `Kano_Model_Guide.md`
- ✅ 使用 PascalCase + 底線: `Document_Quality_Checklist.md`

---

## 📚 相關文檔

- [guides/user/README.md](../user/README.md) - 使用者參考文件目錄說明
- [guides/README.md](../README.md) - Guides 總覽與導航
- [FILE_DIRECTORY_RULES.md](../../FILE_DIRECTORY_RULES.md) - 檔案目錄維護規則

---

**最後更新**: 2026-04-11
