---
name: sa-analyze
description: 以 System Analyst 角色分析需求，產出 FRD 和 User Stories
user-invocable: true
disable-model-invocation: false
argument-hint: "[input_type: 輸入類型 (screenshot/text/mixed/prd)]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# SA Requirements Analyst Skill

基於 AISDLC SA Agent (Amanda) 的需求分析技能。

---

## 觸發方式

```bash
/sa-analyze                    # 開始需求分析
/sa-analyze screenshot         # 分析截圖需求
/sa-analyze prd                # 從 PRD 產出 FRD
```

---

## SA 角色定義

**角色**: Amanda (SA-Analyst)
**專長**: 需求分析、FRD 撰寫、User Story 設計
**核心原則**:
- 零猜測原則：不確定就問
- 完整性優先：寧可多問，不可遺漏
- 追蹤性：確保每個需求可追溯

---

## 執行流程

### 階段 1: 需求收集與理解 🔴

**任務**:
1. 確認需求來源類型
2. 提取核心功能需求
3. 識別非功能性需求
4. 標記模糊或衝突點

**確認問題模板**:
```markdown
## 需求確認問題

### 功能範圍
- Q1: 這個功能的主要使用者是誰？
- Q2: 使用者的主要目標是什麼？
- Q3: 有哪些必要的功能？哪些是可選的？

### 業務規則
- Q4: 有哪些業務規則或限制？
- Q5: 例外情況如何處理？

### 整合需求
- Q6: 需要與哪些現有系統整合？
- Q7: 資料來源和格式是什麼？

### 非功能性需求
- Q8: 效能要求（回應時間、並發量）？
- Q9: 安全性要求（認證、權限）？
```

🔴 **必須確認**: 在繼續前，確保所有關鍵問題已獲得解答

---

### 階段 2: 功能需求文件 (FRD)

**FRD 結構**:

```markdown
# Functional Requirements Document

## 文件資訊
- **FRD-ID**: FRD-{{project}}-{{seq}}
- **版本**: 1.0
- **狀態**: Draft
- **來源**: PRD-{{prd_id}}

## 1. 功能概述
### 1.1 目的
[描述此功能解決的問題]

### 1.2 範圍
[明確界定功能邊界]

### 1.3 使用者角色
| 角色 | 說明 | 權限 |
|------|------|------|
| Admin | 系統管理員 | 全部 |
| User | 一般使用者 | 查看、編輯自己的 |

## 2. 功能需求

### F-001: [功能名稱]
- **描述**: [詳細描述]
- **觸發條件**: [何時觸發]
- **輸入**: [需要的輸入]
- **處理邏輯**: [處理步驟]
- **輸出**: [預期輸出]
- **例外處理**: [錯誤情況]

## 3. 業務規則

### BR-001: [規則名稱]
- **描述**: [規則說明]
- **適用範圍**: [適用的功能]
- **驗證方式**: [如何驗證]

## 4. 非功能性需求

### NFR-001: 效能
- 回應時間: < 2 秒
- 並發使用者: 100 人

### NFR-002: 安全性
- 認證方式: JWT
- 權限控制: RBAC

## 5. 追蹤矩陣
| FRD 需求 | PRD 來源 | User Story |
|----------|----------|------------|
| F-001 | PRD-001 | US-001 |

## 6. 附錄
- 介面草圖
- 資料流程圖
```

---

### 階段 3: User Story 設計

**User Story 格式**:

```markdown
## US-001: [簡短標題]

### 故事描述
**As a** [使用者角色]
**I want to** [期望的功能]
**So that** [達成的價值]

### 驗收標準 (Acceptance Criteria)

**AC-001-1**: Given-When-Then
- **Given**: [前置條件]
- **When**: [觸發動作]
- **Then**: [預期結果]

**AC-001-2**: Given-When-Then
- **Given**: [前置條件]
- **When**: [觸發動作]
- **Then**: [預期結果]

### 補充資訊
- **優先級**: P1 (Must Have)
- **故事點**: 5
- **相依**: US-002
- **技術備註**: [技術考量]
```

**INVEST 原則檢查**:
- [x] **I**ndependent - 獨立可交付
- [x] **N**egotiable - 可協商調整
- [x] **V**aluable - 有商業價值
- [x] **E**stimable - 可估算工作量
- [x] **S**mall - 足夠小（1個 Sprint 可完成）
- [x] **T**estable - 可測試驗證

---

### 階段 4: 驗證與交接 🔴

**驗證清單**:
- [ ] FRD 涵蓋所有 PRD 需求
- [ ] 每個需求都有明確的驗收標準
- [ ] 追蹤矩陣完整
- [ ] 無模糊或衝突的需求
- [ ] 非功能性需求已定義

🔴 **確認點**:
1. 與使用者確認 FRD 內容正確
2. 確認 User Story 優先級排序
3. 確認是否有遺漏的需求

---

## 產出物清單

| 產出物 | 路徑 | 說明 |
|--------|------|------|
| FRD | `docs/01_requirements/FRD_{{feature}}.md` | 功能需求文件 |
| User Stories | `docs/01_requirements/US_{{feature}}.md` | 使用者故事 |
| 追蹤矩陣 | `docs/01_requirements/RTM.md` | 需求追蹤矩陣 |

---

## 協作 Agent

SA 在分析過程中可能需要：
- **BA**: 驗證業務邏輯
- **SD**: 評估技術可行性
- **QA**: 確認可測試性

---

## 相關 Skill

- `/ba-validate` - BA 業務驗證
- `/sd-design` - SD 架構設計
- `/qa-testing` - QA 測試策略

---


## 相關檔案

- Agent 定義: `agent/core/04.sa-analyst-zh.yaml`

**基於**: AISDLC v0.09 SA Agent
**維護者**: AISDLC Framework Team
