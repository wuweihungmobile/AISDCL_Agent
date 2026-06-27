---
name: spec-compliance-check
description: 驗證 SDD 文件產出符合規格要求，按文件類型執行詳細格式與完整性檢查
user-invocable: true
disable-model-invocation: false
argument-hint: "[doc_path: 文件路徑] [gate: SCG-0|SCG-1|SCG-2|SCG-3|SCG-4|SCG-5|SCG-6]"
allowed-tools:
  - Read
  - Grep
  - Glob
---

# Spec Compliance Check Skill（SDD 原生）

SDD 三大支柱之 **Spec-First Gate** 的自動驗證子任務。所有 Agent Skill 在產出文件後必須呼叫本 Skill，確保輸出符合 SDD 規格，方可進行 SCG 閘門驗證。

---

## 觸發方式

```bash
/spec-compliance-check                                         # 驗證當前工作目錄所有文件
/spec-compliance-check docs/02_architecture/SRD-OrderSystem.md # 驗證指定文件
/spec-compliance-check SCG-2                                   # 驗證 SCG-2 所需的全部文件
```

---

## 前置條件（SDD Spec-First）

> 本 Skill 無 SCG 前置條件，任何階段均可呼叫。

---

## 執行流程

### 階段 1：文件識別

根據輸入自動識別文件類型（PRD/FRD/SRD/ADR/API Contract/RTM/Test Plan）。

---

### 階段 2：按文件類型執行驗證

#### 📄 PRD（Product Requirements Document）
```
必填欄位:
- [ ] 標題、版本、日期、狀態（Draft/Approved）
- [ ] 產品目標（量化，含 KPI）
- [ ] 目標使用者（Persona 說明）
- [ ] 功能範圍（In Scope / Out of Scope）
- [ ] 成功指標（可量化）
- [ ] 利害關係人清單

格式:
- [ ] 命名: PRD-{SystemName}.md
- [ ] 路徑: docs/01_requirements/
- [ ] 無 F-XXX 格式（PRD 用業務語言，F-XXX 在 FRD）
```

#### 📄 FRD（Functional Requirements Document）
```
必填欄位:
- [ ] FRD-ID、版本、日期、狀態
- [ ] PRD 來源引用（來源: PRD-{SystemName}.md）
- [ ] 功能需求（F-XXX 格式，含觸發/輸入/處理/輸出/例外）
- [ ] 非功能需求（NFR-XXX 格式，已量化）
- [ ] 業務規則（BR-XXX 格式）
- [ ] User Story（US-XXX 格式）
- [ ] 驗收標準（AC-XXX-Y，Given-When-Then）
- [ ] 追溯矩陣（F-XXX → PRD 來源）

格式:
- [ ] 命名: FRD-{SystemName}.md
- [ ] 路徑: docs/01_requirements/
- [ ] ID 格式正確（F-001 而非 F1 或 FR001）
```

#### 📄 SRD（System Requirements Document）
```
必填欄位:
- [ ] 系統概述（目的、範圍）
- [ ] 架構決策摘要（引用 ADR-XXX）
- [ ] C4 模型連結（Context/Container）
- [ ] 技術棧說明（含 ADR 決策依據）
- [ ] API 端點清單（引用 CONTRACT-*.yaml）
- [ ] 資料模型設計
- [ ] 部署架構
- [ ] NFR 對應設計

格式:
- [ ] 命名: SRD-{SystemName}.md（Greenfield）或 AS-IS-SRD-{SystemName}.md（Brownfield）
- [ ] 路徑: docs/02_architecture/
- [ ] 所有 ADR 引用格式為 ADR-NNN
```

#### 📄 ADR（Architecture Decision Record）
```
必填欄位:
- [ ] ADR 序號（ADR-NNN）、標題、Status、Date、Deciders
- [ ] Context（決策背景，說明為何需要此決策）
- [ ] Decision（選擇了什麼，具體說明）
- [ ] Rationale（選擇理由，對比替代方案）
- [ ] Consequences（正面 + 負面影響）
- [ ] Alternatives Considered（至少 2 個替代方案表格）
- [ ] Related Documents（連結 SRD/FRD）

格式:
- [ ] 命名: ADR-{NNN}-{kebab-title}.md
- [ ] 路徑: docs/02_architecture/adr/
- [ ] Status 為有效值: Proposed/Accepted/Deprecated/Superseded
- [ ] NNN 為三位數字（001 而非 1）
```

#### 📄 API Contract（OpenAPI 3.1）
```
必填欄位:
- [ ] openapi: 3.1.0（非 3.0.x 或 2.0）
- [ ] info.title、info.version、info.description
- [ ] 所有端點有 summary
- [ ] 所有端點有 requestBody Schema（POST/PUT/PATCH）
- [ ] 所有端點有 responses（至少 200/400/401/403/404/500）
- [ ] components.schemas 定義（無 inline schema 過長）
- [ ] security schemes 定義（若有認證）

格式:
- [ ] 命名: CONTRACT-{Module}-v{N}.yaml
- [ ] 路徑: docs/02_architecture/api/
- [ ] YAML 語法正確（縮排一致）
```

#### 📄 Consumer Contract（Pact/自定義）
```
必填欄位:
- [ ] consumer、provider 雙方清楚標示
- [ ] interactions（請求/回應範例）
- [ ] 錯誤情境覆蓋
- [ ] version 版本標示

格式:
- [ ] 命名: CONSUMER-CONTRACT-{Service}.yaml
- [ ] 路徑: docs/02_architecture/api/
```

#### 📄 RTM（Requirements Traceability Matrix）
```
必填欄位:
- [ ] EPIC-XXX → F-XXX → US-XXX → AC-XXX-Y → TC-XXX-Y-Z 完整鏈
- [ ] API-XXX 欄位有值（若已到 SCG-3 後）
- [ ] NFR-XXX 追溯
- [ ] Status 欄位（✅/🔄/❌）
- [ ] 覆蓋率統計（已覆蓋 AC 數 / 總 AC 數）

格式:
- [ ] 命名: RTM-{SystemName}.md
- [ ] 路徑: docs/03_testing/
- [ ] Markdown 表格格式正確
```

#### 📄 Test Plan / Test Cases
```
必填欄位:
- [ ] TC-XXX-Y-Z 格式 ID
- [ ] 每個 TC 對應一個 AC-XXX-Y
- [ ] Given-When-Then 格式
- [ ] 優先級（P1/P2/P3）
- [ ] 測試類型標示（Unit/Integration/E2E/Contract）

格式:
- [ ] 命名: TEST-PLAN-{SystemName}.md 或 TEST-CASES-{Feature}.md
- [ ] 路徑: docs/03_testing/
```

---

### 階段 3：輸出驗證報告

```markdown
## Spec Compliance Report

**文件**: {文件路徑}
**驗證時間**: {YYYY-MM-DD HH:mm}
**文件類型**: {PRD/FRD/SRD/ADR/Contract/RTM}
**對應閘門**: SCG-{N}

### 通過項目 ✅
- completeness: {N}/{Total}
- format: {N}/{Total}

### 失敗項目 ❌
- {具體說明}: {缺少的欄位或格式問題}

### 結論
🔴 未通過（需修正 {N} 項）/ 🟢 通過

### 建議修正
1. {具體修正說明}
```

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 說明 |
|--------|------|------|
| 驗證報告（內嵌輸出） | 無需存檔 | 即時輸出至對話 |

> 若作為 SCG 閘門依據，人工執行截圖或摘錄存入 `docs/03_testing/SCG-{N}-REPORT-{System}.md`

---

## 後置動作

- 若全部通過 → 執行 `/sdd-gate SCG-{N}` 正式驗證閘門
- 若有失敗項 → 依報告修正後重新執行 `/spec-compliance-check`

🔷 **本 Skill 是 SCG 閘門的自動驗證前置步驟**

---

## 相關 Skill

- `/sdd-gate` — 完整 SCG 閘門流程（本 Skill 的上層）
- `/adr-generate` — 補建缺少的 ADR
- `/rtm-generate` — 更新 RTM 覆蓋率

---

**基於**: AISDLC-SDD v0.28（SDD 專屬 Skill）
**對應 SDD 原則**: Spec-First Gate（所有 SCG 閘門）
