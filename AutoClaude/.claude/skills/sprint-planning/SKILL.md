---
name: sprint-planning
description: 完整的 Sprint 規劃流程，整合 PM/SA/Dev/QA 協作
user-invocable: true
disable-model-invocation: false
argument-hint: "<sprint_number: Sprint 編號> [duration: Sprint 天數 (預設 14)]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# Sprint Planning Workflow Skill

完整的 Sprint 規劃流程，整合多角色協作。

---

## 觸發方式

```bash
/sprint-planning 1             # 規劃 Sprint 1
/sprint-planning 5 10          # 規劃 Sprint 5，10 天週期
```

---

## 參與角色

| 角色 | Agent | 職責 |
|------|-------|------|
| **PM/PO** | Victoria | 產品目標、優先級決策 |
| **SA** | Amanda | 需求澄清、User Story 細化 |
| **SD** | Marcus | 技術可行性、架構影響 |
| **Dev** | David | 工作量估算、任務拆分 |
| **QA** | Quincy | 測試策略、驗收標準 |

---

## 執行流程

### 階段 1: Sprint 準備 🔴

**PM/PO 輸入**:
- [ ] Sprint 目標定義
- [ ] 候選 User Stories
- [ ] 業務優先級

**確認項目**:
- [ ] 上個 Sprint 回顧完成
- [ ] Backlog 已整理
- [ ] 團隊可用性已確認

🔴 **確認點**: 確認 Sprint 準備就緒

---

### 階段 2: Backlog 精煉

**SA 主導**:

```markdown
## User Story 精煉清單

### US-[XXX]: [標題]

**描述**:
作為 [角色]
我想要 [功能]
以便 [價值]

**驗收標準**:
- [ ] AC-001: [標準1]
- [ ] AC-002: [標準2]

**技術備註**:
- [技術考量]

**依賴**:
- [依賴項]
```

---

### 階段 3: 技術評估

**SD 主導**:

```markdown
## 技術可行性評估

### US-[XXX] 技術評估

**架構影響**: [高/中/低]
**技術風險**: [高/中/低]
**實作建議**:
- [建議1]
- [建議2]

**依賴**:
- [ ] [依賴項]
```

---

### 階段 4: 工作量估算 🔴

**Dev 主導 (Planning Poker)**:

```markdown
## Story Points 估算

| US ID | 標題 | 複雜度 | 不確定性 | SP |
|-------|------|--------|----------|-----|
| US-001 | [標題] | 中 | 低 | 3 |
| US-002 | [標題] | 高 | 中 | 8 |

**Story Points 參考**:
- 1: 半天內完成
- 2: 一天內完成
- 3: 2-3 天
- 5: 一週
- 8: 需拆分
- 13: 必須拆分
```

🔴 **確認點**: 確認估算結果

---

### 階段 5: Sprint 承諾

**團隊決議**:

```markdown
## Sprint [N] 承諾

**Sprint 目標**:
> [目標描述]

**承諾的 User Stories**:

| 優先級 | US ID | 標題 | SP | 負責人 |
|--------|-------|------|----|----- |
| P1 | US-001 | [標題] | 3 | Dev |
| P1 | US-002 | [標題] | 5 | Dev |

**總 SP**: [N] / 團隊容量: [M]
**填充率**: [N/M * 100]%

**風險**:
1. [風險描述] - 緩解措施: [措施]
```

---

### 階段 6: 測試規劃

**QA 主導**:

```markdown
## Sprint [N] 測試策略

**測試範圍**:
- [ ] US-001: [測試重點]
- [ ] US-002: [測試重點]

**測試類型**:
- [ ] 單元測試 (Dev)
- [ ] 整合測試 (QA)
- [ ] E2E 測試 (QA)

**測試環境**:
- [ ] 環境準備就緒
```

---

### 階段 7: 輸出文檔 🔴

**最終產出**:

```markdown
# Sprint [N] Plan

## Sprint 資訊
- **編號**: Sprint [N]
- **期間**: [開始] - [結束]
- **容量**: [N] SP

## Sprint 目標
> [目標]

## User Stories

| ID | 標題 | SP | 負責人 | AC 數 |
|----|------|----|----- |-------|
| US-001 | [標題] | 3 | Dev | 3 |

## 任務分解

### US-001: [標題]
- [ ] Task 1: [描述] (2h)
- [ ] Task 2: [描述] (4h)

## 風險與依賴
- [內容]

## Definition of Done
- [ ] 代碼完成且通過 Review
- [ ] 單元測試覆蓋率 >= 80%
- [ ] 整合測試通過
- [ ] 文檔更新
```

🔴 **確認點**: 確認 Sprint 計劃完成

---

## 產出物

| 產出物 | 路徑 |
|--------|------|
| Sprint 計劃 | `docs/04_planning/SPRINT_[N]_PLAN.md` |
| 任務分解 | `docs/05_development/SPRINT_[N]_TASKS.md` |
| 測試計劃 | `docs/03_testing/SPRINT_[N]_TEST_PLAN.md` |

---

## 相關 Skill

- `/pm-planning` - PM 產品規劃
- `/sa-analyze` - SA 需求分析
- `/release-management` - 發布管理

---


## 相關檔案

- Workflow 定義: `workflow/core/`

**基於**: AISDLC v0.09 Workflow
