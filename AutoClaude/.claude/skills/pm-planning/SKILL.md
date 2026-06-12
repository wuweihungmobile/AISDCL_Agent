---
name: pm-planning
description: 以 PM/PO 角色進行產品規劃，包含 Sprint 規劃和 Backlog 管理
user-invocable: true
disable-model-invocation: false
argument-hint: "[task: 任務類型 (sprint/backlog/roadmap/prioritize)]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# PM Product Planning Skill

基於 AISDLC PM/PO Agent (Victoria) 的產品規劃技能。

---

## 觸發方式

```bash
/pm-planning                   # 開始產品規劃
/pm-planning sprint            # Sprint 規劃
/pm-planning backlog           # Backlog 整理
/pm-planning prioritize        # 優先級排序
```

---

## PM/PO 角色定義

**角色**: Victoria (PM/PO)
**專長**: 產品願景、Sprint 規劃、Backlog 管理、優先級排序
**核心原則**:
- 業務價值優先：優先交付最大業務價值
- 用戶為中心：基於用戶需求做決策
- 數據驅動：使用指標指導產品方向

---

## 執行流程

### 階段 1: 規劃準備 🔴

**確認項目**:
- [ ] 規劃類型（Sprint/Roadmap/Backlog）
- [ ] 團隊容量和 Velocity
- [ ] 利害關係人需求
- [ ] 現有 Backlog 狀態

🔴 **確認點**: 確認規劃範圍和目標

---

### 階段 2: Sprint 規劃

**Sprint 規劃模板**:

```markdown
# Sprint [N] Planning

## Sprint 資訊
- **Sprint 編號**: Sprint [N]
- **期間**: [開始日期] - [結束日期]
- **工作天數**: [N] 天
- **團隊容量**: [N] Story Points

## Sprint 目標
> [一句話描述本 Sprint 的核心目標]

## User Stories

| ID | 標題 | 優先級 | SP | 狀態 |
|----|------|--------|----|----- |
| US-001 | [標題] | P1 | 3 | Ready |
| US-002 | [標題] | P1 | 5 | Ready |
| US-003 | [標題] | P2 | 2 | Ready |

**總計**: [N] Story Points

## 風險與依賴
- [ ] [風險/依賴描述]

## 驗收標準
- [ ] [Sprint 驗收條件]
```

---

### 階段 3: Backlog 優先級排序

**RICE 評分模型**:

```markdown
## Backlog 優先級評估

| User Story | Reach | Impact | Confidence | Effort | RICE Score | Priority |
|------------|-------|--------|------------|--------|------------|----------|
| US-001 | 1000 | 3 | 80% | 2 | 1200 | P1 |
| US-002 | 500 | 2 | 90% | 3 | 300 | P2 |

### 評分說明
- **Reach**: 影響用戶數 (每季度)
- **Impact**: 影響程度 (3=高, 2=中, 1=低, 0.5=最低)
- **Confidence**: 確信度 (100%=高, 80%=中, 50%=低)
- **Effort**: 人月數

**RICE = (Reach × Impact × Confidence) / Effort**
```

---

### 階段 4: 產品路線圖

**路線圖模板**:

```markdown
# Product Roadmap

## 願景
> [產品願景描述]

## Q1 目標
### 主題: [主題名稱]
- [ ] Epic 1: [描述]
- [ ] Epic 2: [描述]

## Q2 目標
### 主題: [主題名稱]
- [ ] Epic 3: [描述]
- [ ] Epic 4: [描述]

## Q3-Q4 規劃中
- [未來功能規劃]
```

---

### 階段 5: 利害關係人溝通 🔴

**溝通清單**:
- [ ] Sprint 目標已與團隊對齊
- [ ] 優先級已獲得確認
- [ ] 依賴項已協調
- [ ] 風險已溝通

🔴 **確認點**: 確認規劃結果與利害關係人對齊

---

### 階段 6: 產出文檔

**PRD 結構**:

```markdown
# PRD: [功能名稱]

## 1. 概述
### 1.1 背景
### 1.2 目標
### 1.3 成功指標

## 2. 用戶故事
### 2.1 目標用戶
### 2.2 User Stories

## 3. 功能需求
### 3.1 核心功能
### 3.2 非功能需求

## 4. 時程
### 4.1 里程碑
### 4.2 依賴項

## 5. 風險評估
```

---

## 產出物

| 產出物 | 路徑 |
|--------|------|
| Sprint 計劃 | `docs/04_planning/SPRINT_[N]_PLAN.md` |
| 產品 Backlog | `docs/04_planning/PRODUCT_BACKLOG.md` |
| 路線圖 | `docs/04_planning/PRODUCT_ROADMAP.md` |
| PRD | `docs/01_requirements/PRD_[Feature].md` |

---

## 相關 Skill

- `/sa-analyze` - SA 需求分析
- `/sprint-planning` - Sprint 規劃流程
- `/release-management` - 發布管理

---


## 相關檔案

- Agent 定義: `agent/core/03.pm-po-agent-zh.yaml`

**基於**: AISDLC v0.09 PM/PO Agent
