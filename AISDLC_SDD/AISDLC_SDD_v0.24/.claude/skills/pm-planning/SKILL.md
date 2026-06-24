---
name: pm-planning
description: 以 PM/PO 角色進行產品規劃，產出 PRD，協助 SCG-0 需求凍結，確保 Sprint 中每個 Story 有 FRD 追溯
user-invocable: true
disable-model-invocation: false
argument-hint: "[task: prd|sprint|backlog|roadmap|prioritize]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# PM 產品規劃 Skill（SDD 原生）

PM 是 SDD 需求階段的業務目標定義者。本 Skill 產出 PRD，與 SA 的 FRD 共同構成 SCG-0 的必要文件。在 Sprint 規劃中，每個 Story 必須追溯到 FRD 的 F-XXX，確保所有開發工作有規格依據。

---

## 觸發方式

```bash
/pm-planning prd               # 產出 PRD（SCG-0 前置）
/pm-planning sprint            # Sprint 規劃（需 SCG-0 通過後）
/pm-planning backlog           # Backlog 整理與優先級排序
/pm-planning roadmap           # 產品路線圖
/pm-planning prioritize        # 需求優先級排序（RICE 模型）
```

---

## 前置條件（SDD Spec-First）

| 執行任務 | 前置條件 | 說明 |
|---------|---------|------|
| prd | 無（PM 工作流起點） | 業務願景/需求輸入 |
| sprint | 🔷 SCG-0 通過 | FRD 已凍結，才能確認 Sprint Story |
| backlog/roadmap/prioritize | PRD 已存在 | 需求已初步定義 |

---

## 執行流程

---

### 任務 A：PRD 產出（SCG-0 前置）

**文件路徑**：`docs/01_requirements/PRD-{SystemName}.md`
**範本來源**：`docs_template/core/prd/PRD_Universal_Template.md`

```markdown
# Product Requirements Document — {SystemName}

**PRD-ID**: PRD-{System}-{seq}
**版本**: 1.0
**日期**: {YYYY-MM-DD}
**狀態**: Draft → Approved
**作者**: PM Agent (Victoria)

## 1. 產品概述

### 1.1 背景與問題
{描述當前問題或機會，說明為什麼需要這個產品/功能}

### 1.2 產品目標
{SMART 目標：具體、可量化、可達成、相關、有時間限制}

### 1.3 成功指標（KPI）
| 指標 | 基線 | 目標 | 量測方式 |
|------|------|------|---------|
| {指標 A} | {現況} | {目標值} | {如何量測} |

## 2. 目標使用者

| Persona | 角色 | 主要痛點 | 主要目標 |
|---------|------|---------|---------|
| {Persona A} | {職位/角色} | {痛點} | {目標} |

## 3. 功能範圍

### In Scope
- {功能 A}（業務語言描述，非技術）
- {功能 B}

### Out of Scope
- {明確排除的功能}

## 4. 業務規則（高層）
- BR-H001: {業務規則（SA 會轉化為 FRD 中的 BR-XXX）}

## 5. 非功能性需求（業務視角）
- 效能：{業務場景描述，如「1000 人同時下單」}
- 可用性：{SLA 要求，如「99.9% 可用性」}
- 安全：{資料敏感度等級}

## 6. 時程與里程碑
| 里程碑 | 目標日期 | 說明 |
|--------|---------|------|
| SCG-0 需求凍結 | {date} | FRD 完成，需求不再變更 |
| SCG-3 開發啟動 | {date} | Contract 凍結，開始實作 |
| SCG-6 發布 | {date} | 上線 |

## 7. 利害關係人
| 利害關係人 | 角色 | 期望 |
|-----------|------|------|

## 8. 風險評估
| 風險 | 機率 | 影響 | 緩解策略 |
|------|------|------|---------|
```

🔴 確認點：PRD 需利害關係人確認後，才能啟動 SA 分析（`/sa-analyst`）。

---

### 任務 B：Sprint 規劃（SCG-0 通過後）

**前置確認**：讀取 `docs/01_requirements/FRD-{SystemName}.md` 確認 F-XXX/US-XXX 清單。

```markdown
# Sprint {N} Planning

## Sprint 資訊
- **Sprint 編號**: Sprint {N}
- **期間**: {開始日期} - {結束日期}（{N} 工作天）
- **團隊容量**: {N} Story Points

## Sprint 目標
> {一句話說明核心業務目標，需對應 PRD 的功能範圍}

## User Stories（FRD 追溯）

| US-ID | 標題 | FRD Feature | 優先級 | SP | 狀態 |
|-------|------|------------|--------|----|----- |
| US-001 | {標題} | F-001 | P1 | 3 | Ready |
| US-002 | {標題} | F-002 | P1 | 5 | Ready |

> 🔴 **SDD 規則**: 每個 US-XXX 必須有對應的 FRD F-XXX，無 F-XXX 的 Story 不可進入 Sprint。

## SCG 確認
- [ ] 本 Sprint 所有 Story 對應的 FRD Feature 已在 SCG-0 凍結
- [ ] 若有新需求，必須先更新 FRD 並重新通過 SCG-0

## 風險與依賴
| 風險/依賴 | 影響 | 緩解措施 |
|---------|------|---------|

## Sprint 驗收標準
- [ ] 所有 Story 的 AC 測試通過（TC-XXX）
- [ ] RTM 更新完成
```

---

### 任務 C：Backlog 優先級排序（RICE 模型）

```markdown
## Backlog 優先級評估（RICE 模型）

| US-ID | 標題 | Reach | Impact | Confidence | Effort | RICE Score | Priority |
|-------|------|-------|--------|------------|--------|------------|----------|
| US-{N} | {標題} | {用戶數/季} | 3/2/1/0.5 | 100/80/50% | {人月} | {計算} | P1/P2/P3 |

**RICE = (Reach × Impact × Confidence) / Effort**
```

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| PRD | `docs/01_requirements/PRD-{SystemName}.md` | SCG-0 前 |
| Sprint 計畫（每 Sprint） | `docs/04_planning/SPRINT-{N}-PLAN.md` | SCG-0 通過後 |
| Product Backlog | `docs/04_planning/PRODUCT-BACKLOG.md` | 持續維護 |
| Product Roadmap | `docs/04_planning/PRODUCT-ROADMAP.md` | 季度更新 |

---

## 後置動作

**PRD 完成後**：
```
/sa-analyst prd    # SA 從 PRD 產出 FRD
/ba-analyst prd   # BA 驗證 PRD 業務對齊
```

**Sprint 規劃後**：
```
/sprint-planning   # 完整 Sprint 啟動流程
```

🔷 **本 Skill 協助通過**：SCG-0（Requirement Spec Gate）— 提供 PRD 作為必要文件

---

## 相關 Skill

- `/sa-analyst` — 需求分析（PRD → FRD 轉化）
- `/ba-analyst` — 業務驗證（PRD 驗證）
- `/sprint-planning` — Sprint 啟動（Sprint 規劃的完整流程）
- `/release-management` — 發布管理（產品路線圖執行）
- `/sdd-gate SCG-0` — 需求凍結閘門

---

**基於**: AISDLC-SDD v0.24
**對應 Agent**: `03.pm-po-agent-zh.yaml`
**對應 SDD Enhancement**: `scenarios/greenfield/SDD_GREENFIELD_ENHANCEMENT.md`
