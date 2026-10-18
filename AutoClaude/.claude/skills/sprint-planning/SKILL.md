---
name: sprint-planning
description: 執行完整 Sprint 規劃流程，確保每個 User Story 有 FRD 追溯，SCG-0 通過後才能啟動 Sprint
user-invocable: true
disable-model-invocation: false
argument-hint: "<sprint_number: Sprint 編號> [duration: Sprint 天數 (預設 14)]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# Sprint Planning Workflow Skill（SDD 原生）

Sprint 是 SDD 規格驅動執行的單元。本 Skill 確保每個進入 Sprint 的 Story 都有 FRD 追溯（F-XXX），且 Sprint 在 SCG-0 需求凍結後才能啟動。所有 Story 必須對應 Contract 凍結後的 API。

---

## 觸發方式

```bash
/sprint-planning 1             # 規劃 Sprint 1
/sprint-planning 5 10          # 規劃 Sprint 5，10 天週期
```

---

## 前置條件（SDD Spec-First）

| 閘門 | 說明 | 驗證方式 |
|------|------|---------|
| 🔷 SCG-0 通過 | 需求凍結，FRD 已確定 | `/sdd-gate SCG-0` 報告存在 |
| FRD 存在 | US-XXX/F-XXX 清單已定義 | `docs/01_requirements/FRD-{System}.md` |

> 若 SCG-0 尚未通過，先執行 `/sa-analyst` → `/ba-analyst` → `/sdd-gate SCG-0`

---

## 執行流程

### 階段 1：Sprint 準備（FRD 確認）

讀取 FRD 取得 Backlog：

```bash
docs/01_requirements/FRD-{SystemName}.md   # 讀取 F-XXX/US-XXX 清單
docs/04_planning/PRODUCT-BACKLOG.md        # 讀取優先級排序
docs/03_testing/RTM-{SystemName}.md        # 確認哪些 US 尚未有 TC
```

確認清單：
- [ ] 上個 Sprint 回顧完成（若非 Sprint 1）
- [ ] Backlog 已整理並優先排序（RICE 模型）
- [ ] 團隊容量已確認（Story Points 總量）

🔴 確認點：確認候選 US 清單，每個 US 必須對應 FRD 中的 F-XXX。

---

### 階段 2：User Story 精煉（FRD 追溯確認）

對每個候選 US 確認 FRD 追溯：

```markdown
## Sprint {N} 候選 User Stories

### US-{NNN}: {標題}
**FRD Feature 追溯**: F-{NNN}（`FRD-{SystemName}.md` 第 X 節）

**描述**:
As a {角色}
I want to {功能}
So that {業務價值}

**驗收標準**（來自 FRD AC-XXX-Y）:
- AC-{NNN}-1: Given {前置} When {動作} Then {預期}
- AC-{NNN}-2: Given {前置} When {動作} Then {預期}

**API 依賴**（SCG-3 後）:
- API-{NNN}: {端點說明}（Contract 已凍結）

🔴 **SDD 規則**: US 無 F-XXX 追溯 → 不可進入 Sprint，必須先更新 FRD 並重新確認 SCG-0
```

---

### 階段 3：技術評估

SD 確認技術可行性：

```markdown
## US-{NNN} 技術評估

**架構影響**: 高/中/低
- 若影響架構 → 需要新 ADR（`/adr-generate`）
- 若影響 API → 需更新 Contract（`/contract-generate`）並重新確認 SCG-3

**技術風險**: 高/中/低
**實作方案**: {簡要說明}
**依賴項**: {外部依賴/其他 US}
```

---

### 階段 4：工作量估算 🔴

```markdown
## Story Points 估算（Planning Poker）

| US-ID | 標題 | F-XXX | 複雜度 | 不確定性 | SP |
|-------|------|-------|--------|---------|-----|
| US-{N} | {標題} | F-{N} | 中 | 低 | 3 |

**團隊容量**: {N} SP
**本 Sprint 承諾**: {N} SP（填充率 ≤ 85%）

SP 參考:
- 1: 半天（簡單修改）
- 3: 2-3 天（標準功能）
- 5: 一週（複雜功能）
- 8+: 必須拆分
```

🔴 確認點：確認估算合理，8+ SP 的 US 必須拆分。

---

### 階段 5：Sprint 計畫文件產出 🔴

**文件路徑**：`docs/04_planning/SPRINT-{N}-PLAN.md`

```markdown
# Sprint {N} Plan

## Sprint 資訊
- **期間**: {開始日期} - {結束日期}（{N} 天）
- **容量**: {N} SP
- **SCG-0 基準**: {SCG-0 通過日期}

## Sprint 目標
> {業務語言描述的 Sprint 核心目標}

## User Stories（FRD 追溯）

| US-ID | 標題 | F-XXX | SP | 負責人 | AC 數 |
|-------|------|-------|----|----- |-------|
| US-{N} | {標題} | F-{N} | 3 | Dev | 2 |

**總 SP**: {N} / **容量**: {N}（填充率 {%}%）

## Definition of Done（SDD 版）
- [ ] 代碼實作完成（符合 Contract 規格）
- [ ] 單元測試覆蓋率 ≥ 80%
- [ ] Contract Testing 通過
- [ ] `/dev-review spec-compliance` 通過（規格一致性確認）
- [ ] RTM 更新（TC 狀態更新為 ✅）
- [ ] `/spec-compliance-check` 通過

## 風險與依賴
| 風險 | 影響 | 緩解措施 |
|------|------|---------|
```

1. 執行 `/spec-compliance-check docs/04_planning/SPRINT-{N}-PLAN.md`
2. 🔴 確認點：Sprint Goal 和 US 清單需 PM 確認

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| Sprint 計畫 | `docs/04_planning/SPRINT-{N}-PLAN.md` | SCG-0 後 |
| Sprint 任務分解 | `docs/05_development/SPRINT-{N}-TASKS.md` | SCG-0 後 |

---

## 後置動作

```
/qa-testing                    # QA 確認本 Sprint 的測試範圍
/devops-github-actions      # 確認 CI/CD 流水線就緒
```

🔷 **本 Skill 在 SCG 框架中的定位**：SCG-0 通過後、SCG-3 前的執行規劃層

---

## 相關 Skill

- `/pm-planning sprint` — PM Sprint 準備
- `/sa-analyst` — 若 Story 需求不清，退回 SA 補充 FRD
- `/sdd-gate SCG-0` — 必須通過才能啟動 Sprint
- `/release-management` — Sprint 完成後的發布流程

---

**基於**: AISDLC-SDD v0.30
**對應工作流**: `workflow/core/SPRINT_WORKFLOW.md`
**對應 SDD Enhancement**: `scenarios/greenfield/SDD_GREENFIELD_ENHANCEMENT.md`
