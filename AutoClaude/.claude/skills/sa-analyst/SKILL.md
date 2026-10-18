---
name: sa-analyst
description: 以 System Analyst 角色分析需求，產出 FRD、User Stories 和 RTM 初版，準備 SCG-0 需求凍結閘門
user-invocable: true
disable-model-invocation: false
argument-hint: "[input_type: screenshot|text|mixed|prd] [scenario: greenfield|brownfield|refactoring]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# SA 需求分析 Skill（SDD 原生）

SA 是 SDD 工作流的起點。本 Skill 產出 FRD、User Stories 和 RTM 初版，為 SCG-0 需求凍結閘門提供必要文件。Brownfield 情境下，本 Skill 需在 `/brownfield-analysis` 後執行。

---

## 觸發方式

```bash
/sa-analyst                        # Greenfield：從 PRD 或會議記錄開始
/sa-analyst screenshot             # 從截圖分析需求
/sa-analyst prd                    # 從現有 PRD 產出 FRD
/sa-analyst brownfield             # Brownfield：讀取 As-Is SRD 後分析 Gap
/sa-analyst refactoring            # Refactoring：讀取 Business Invariants 後分析
```

---

## 前置條件（SDD Spec-First）

| 情境 | 前置條件 | 說明 |
|------|---------|------|
| Greenfield | 無（本 Skill 是起點） | 確認 PRD 草稿或需求輸入存在 |
| Brownfield | `/brownfield-analysis` 已完成 | 需要 As-Is SRD 作為基線 |
| Refactoring | Business Invariants 清單已確認 | INV-XXX 清單是重構邊界 |

---

## 執行流程

### 階段 1：情境確認與前置讀取

**1.1 確認執行情境**（Greenfield / Brownfield / Refactoring）

**1.2 Brownfield 情境前置讀取**（若 `scenario: brownfield`）：
- 讀取 `docs/02_architecture/AS-IS-SRD-{System}.md`
- 讀取 `docs/04_planning/GAP-ANALYSIS-{System}.md`
- 確認哪些功能是新增 vs. 修改 vs. 保留

**1.3 Refactoring 情境前置讀取**：
- 讀取 `docs/01_requirements/INVARIANT-SPEC-{System}.md`
- 確認 INV-XXX 清單（不可破壞的業務不變量）

🔴 **確認點**：Brownfield/Refactoring 情境，前置文件必須存在才能繼續。

---

### 階段 2：需求收集與澄清 🔴

提出確認問題：

```markdown
## 需求確認問題

### 功能範圍
- Q1: 這個功能的主要使用者是誰？（影響 US 設計）
- Q2: 核心使用流程是什麼？（影響 AC 設計）
- Q3: 哪些是 Must Have？哪些是 Nice to Have？

### 業務規則
- Q4: 有哪些業務規則或限制（BR-XXX）？
- Q5: 例外情況如何處理？

### 非功能性需求（必須量化）
- Q6: 回應時間要求（P99）？並發量？
- Q7: 安全等級要求（認證/授權/加密）？
- Q8: 可用性 SLA？

### 整合需求
- Q9: 需要整合哪些現有系統或第三方服務？
- Q10: 資料來源和格式是什麼？
```

🔴 **確認點**：所有 Q1~Q10 必須有明確答案後才繼續。

---

### 階段 3：功能需求文件（FRD）產出

**文件路徑**：`docs/01_requirements/FRD-{SystemName}.md`
**範本來源**：`docs_template/core/frd/FRD_Universal_Template.md`

**FRD 必要結構**：

```markdown
# Functional Requirements Document — {SystemName}

**FRD-ID**: FRD-{System}-{seq}
**版本**: 1.0
**日期**: {YYYY-MM-DD}
**狀態**: Draft
**來源**: PRD-{SystemName}.md（或需求來源說明）

## 1. 功能需求

### F-001: {功能名稱}
- **描述**: {詳細描述}
- **觸發條件**: {何時觸發}
- **輸入**: {需要的輸入}
- **處理邏輯**: {業務邏輯步驟}
- **輸出**: {預期輸出}
- **例外處理**: {錯誤情況}
- **來源**: PRD-{Section}

## 2. 業務規則

### BR-001: {規則名稱}
- **描述**: {規則說明}
- **適用範圍**: {F-XXX}
- **違規處理**: {如何處理違規}

## 3. 非功能性需求（量化）

### NFR-001: 效能
- **P50 回應時間**: < {N} ms
- **P99 回應時間**: < {N} ms
- **並發使用者**: {N}
- **吞吐量**: {N} req/s

### NFR-002: 安全性
- **認證方式**: {JWT/OAuth2/API Key}
- **授權模型**: {RBAC/ABAC}
- **資料加密**: {傳輸/靜態}

## 4. User Stories

### US-001: {標題}
**As a** {使用者角色}
**I want to** {期望功能}
**So that** {業務價值}

**驗收標準**:
- **AC-001-1**: Given {前置條件} When {觸發} Then {預期結果}
- **AC-001-2**: Given {前置條件} When {觸發} Then {預期結果}

**INVEST 原則**: ✅ 獨立 ✅ 可協商 ✅ 有價值 ✅ 可估算 ✅ 夠小 ✅ 可測試

## 5. Invariant Spec（Refactoring 情境必填）

### INV-001: {不變量名稱}
- **描述**: {業務約束，重構前後不可改變}
- **驗證方式**: {如何自動驗證}
- **對應 AC**: {AC-XXX-Y}
```

---

### 階段 4：RTM 初版建立（嵌入流程）

FRD 產出後**立即**執行 RTM 初版建立：

```bash
/rtm-generate full docs/01_requirements/FRD-{SystemName}.md
```

RTM 初版只填入 EPIC/Feature/US/AC 欄位，API 和 TC 欄位留空（稍後填入）。

---

### 階段 5：文件驗證與 SCG-0 準備 🔴

1. 執行 `/spec-compliance-check docs/01_requirements/FRD-{SystemName}.md`
2. 確認驗證報告全部通過
3. 確認清單：
   - [ ] FRD 涵蓋所有 PRD 需求（無遺漏）
   - [ ] 每個 US 都有至少 2 個 AC（Given-When-Then 格式）
   - [ ] NFR 已量化（P99/並發量/SLA）
   - [ ] RTM 初版建立完成（覆蓋率 > 0%）
   - [ ] Brownfield：已標注 As-Is → To-Be 差異
   - [ ] Refactoring：INV-XXX 清單已確認

🔴 **確認點**：FRD 內容需與使用者/利害關係人確認後才能凍結。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| FRD | `docs/01_requirements/FRD-{SystemName}.md` | SCG-0 |
| User Stories | FRD 內 US 章節 | SCG-0 |
| RTM 初版 | `docs/03_testing/RTM-{SystemName}.md` | SCG-0 |
| Invariant Spec（Refactoring） | `docs/01_requirements/INVARIANT-SPEC-{SystemName}.md` | SCG-0 |

---

## 後置動作

```
/ba-analyst prd       # BA 驗證需求業務對齊
/rtm-generate verify   # 確認 RTM 初版完整
/sdd-gate SCG-0        # 需求凍結閘門
```

🔷 **本 Skill 協助通過**：SCG-0（Requirement Spec Gate）

---

## 相關 Skill

- `/ba-analyst` — 業務驗證（SCG-0 協同）
- `/brownfield-analysis` — Brownfield 前置（as-is 規格化）
- `/rtm-generate` — 追溯矩陣（FRD 完成後立即執行）
- `/sd-architect` — 架構設計（SCG-0 通過後接棒）
- `/sdd-gate SCG-0` — 需求凍結閘門

---

**基於**: AISDLC-SDD v0.30
**對應 Agent**: `04.sa-analyst-zh.yaml`
**對應 SDD Enhancement**: `scenarios/greenfield/SDD_GREENFIELD_ENHANCEMENT.md`
