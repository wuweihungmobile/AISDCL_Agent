---
name: ba-validate
description: 以 Business Analyst 角色驗證需求業務對齊，管理利害關係人，協助通過 SCG-0 需求凍結閘門
user-invocable: true
disable-model-invocation: false
argument-hint: "[validation_type: prd|frd|user-story|process|stakeholder]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# BA 業務需求驗證 Skill（SDD 原生）

BA 是 SCG-0 閘門的業務對齊守門員。本 Skill 在 SA 完成 FRD 後執行，從業務視角驗證需求、管理利害關係人共識，確保需求在凍結前符合業務現實。

---

## 觸發方式

```bash
/ba-validate                   # 全面驗證（PRD + FRD + 利害關係人）
/ba-validate prd               # 驗證 PRD 業務需求
/ba-validate frd               # 驗證 FRD 功能對齊
/ba-validate user-story        # 驗證 User Story 業務價值
/ba-validate stakeholder       # 利害關係人分析
```

---

## 前置條件（SDD Spec-First）

| 閘門/文件 | 說明 | 驗證方式 |
|---------|------|---------|
| FRD 草稿存在 | `/sa-analyze` 已執行 | `docs/01_requirements/FRD-{System}.md` 存在 |
| PRD 草稿存在 | 需求輸入源 | `docs/01_requirements/PRD-{System}.md` 或等效文件 |

---

## 執行流程

### 階段 1：利害關係人識別 🔴

建立利害關係人矩陣：

```markdown
## 利害關係人矩陣

| 利害關係人 | 角色 | 影響力 | 主要關注點 | 參與需求 |
|-----------|------|--------|-----------|---------|
| {姓名/角色} | {職位} | 高/中/低 | {業務關注} | 確認/{專項} |
```

🔴 **確認點**：確保所有關鍵利害關係人已識別，缺少任何一方可能導致需求遺漏。

---

### 階段 2：PRD 業務驗證

```markdown
## PRD 業務驗證清單

### 商業目標
- [ ] 商業目標明確且可量化（附 KPI）
- [ ] 成功指標可衡量（非模糊描述）
- [ ] ROI 估算合理且有業務依據

### 使用者需求
- [ ] 目標使用者明確定義（Persona）
- [ ] 使用者痛點已驗證（非假設）
- [ ] 使用者旅程完整（無斷點）

### 業務規則
- [ ] 業務規則完整記錄（BR-XXX 格式）
- [ ] 例外情況已處理（含邊界條件）
- [ ] 與現有業務流程整合考量完整

### 風險評估
- [ ] 業務風險已識別（含概率/影響）
- [ ] 緩解策略已定義且可執行
```

---

### 階段 3：FRD 業務功能驗證

```markdown
## FRD 功能驗證清單

### 功能完整性
- [ ] 所有 PRD 需求已轉化為 F-XXX（無遺漏）
- [ ] 功能邊界清晰（In Scope / Out of Scope）
- [ ] 相依關係明確（F-XXX depends on F-YYY）

### 業務邏輯
- [ ] 業務規則在 F-XXX 中正確體現（BR-XXX 引用）
- [ ] 計算邏輯已驗證（含公式/規則）
- [ ] 資料流程合理且無業務衝突

### 使用者體驗
- [ ] 功能符合目標使用者的實際操作習慣
- [ ] AC 的 Given-When-Then 從使用者視角描述（非技術視角）
- [ ] 錯誤訊息對使用者友善（非系統錯誤碼）

### 非功能性需求業務合理性
- [ ] 效能 NFR 基於業務情境（非拍腦袋）
- [ ] 安全 NFR 符合資料敏感度要求
- [ ] SLA 可用性符合業務連續性需求
```

---

### 階段 4：業務流程驗證（As-Is → To-Be）🔴

```markdown
## 業務流程驗證報告 — {流程名稱}

### As-Is 流程
{現有業務流程描述（人工作業或舊系統）}

### To-Be 流程
{系統實現後的新流程}

### 差異分析
| 流程步驟 | As-Is | To-Be | 影響 | 需要變更管理？ |
|---------|-------|-------|------|-------------|
| {步驟} | {現況} | {目標} | 高/中/低 | 是/否 |

### 風險評估
| 風險 | 機率 | 影響 | 緩解策略 |
|------|------|------|---------|
| {風險} | 高/中/低 | 高/中/低 | {策略} |
```

🔴 **確認點**：業務流程變更必須獲得利害關係人明確同意。

---

### 階段 5：驗證結論與 SCG-0 建議 🔴

產出驗證結論：

```markdown
## 需求驗證結論 — {SystemName}

**日期**: {YYYY-MM-DD}
**驗證者**: BA Agent (Beatrice)
**驗證範圍**: {PRD/FRD/User Story}

### 通過項目 ✅
- {項目清單}

### 待修改項目 ❌
| 項目 | 問題 | 建議修改 | 負責人 |
|------|------|---------|-------|
| {需求 ID} | {問題} | {建議} | SA |

### SCG-0 建議
🟢 建議通過 / 🔴 需修正後再次驗證

### 利害關係人簽核
- [ ] {利害關係人 A} 確認
- [ ] {利害關係人 B} 確認
```

1. 執行 `/spec-compliance-check docs/01_requirements/FRD-{SystemName}.md`
2. 🔴 確認點：驗證結果需獲得各方簽核

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| 利害關係人分析 | `docs/01_requirements/STAKEHOLDER-{SystemName}.md` | SCG-0 前 |
| 需求驗證報告 | `docs/01_requirements/BA-VALIDATION-{SystemName}.md` | SCG-0 |
| 業務流程驗證 | `docs/01_requirements/PROCESS-VALIDATION-{SystemName}.md` | SCG-0 |

---

## 後置動作

```
/sdd-gate SCG-0    # BA 驗證通過後，執行需求凍結閘門
```

🔷 **本 Skill 協助通過**：SCG-0（Requirement Spec Gate）

---

## 相關 Skill

- `/sa-analyze` — 需求分析（本 Skill 的前置）
- `/pm-planning` — 產品規劃（業務目標對齊）
- `/sdd-gate SCG-0` — 需求凍結閘門（BA 驗證是必要條件之一）

---

**基於**: AISDLC-SDD v0.01
**對應 Agent**: `02.ba-business-analyst-zh.yaml`
**對應 SDD Enhancement**: `scenarios/greenfield/SDD_GREENFIELD_ENHANCEMENT.md`
