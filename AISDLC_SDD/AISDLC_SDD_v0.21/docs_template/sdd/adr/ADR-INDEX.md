# Architecture Decision Records 索引
# ADR Index

**專案**: {PROJECT_NAME}
**最後更新**: YYYY-MM-DD
**維護者**: technical-writer（`adr_index_maintenance` Skill）
**觸發 Skill**: `adr_index_maintenance`

---

## 使用說明

本索引由 `technical-writer` 的 `adr_index_maintenance` Skill 自動維護。
每次新增 ADR 後，必須立即更新本索引。

---

## ADR 狀態說明

| 狀態 | 說明 |
|------|------|
| 🟡 Proposed | 已提出，待 Human 確認 |
| ✅ Accepted | 已確認，成為正式決策 |
| 🚫 Deprecated | 已廢棄（技術過時）|
| 🔄 Superseded | 被新 ADR 取代 |

---

## ADR 列表

| 編號 | 標題 | 狀態 | 日期 | 決策者 | 關聯文件 |
|------|------|------|------|--------|---------|
| [ADR-001](ADR-001-example.md) | _(範例)技術棧選擇_ | ✅ Accepted | YYYY-MM-DD | sd-architect | SRD |
| [ADR-002](ADR-002-example.md) | _(範例)架構模式選擇_ | ✅ Accepted | YYYY-MM-DD | sd-architect | SRD |
| [ADR-003](ADR-003-example.md) | _(範例)部署策略_ | ✅ Accepted | YYYY-MM-DD | sd-architect | SRD |

> **提示**：刪除上方範例行，加入實際 ADR 記錄。

---

## ADR 統計

| 統計項目 | 數量 |
|---------|------|
| 總 ADR 數 | 0 |
| Accepted | 0 |
| Proposed | 0 |
| Deprecated | 0 |
| Superseded | 0 |

---

## ADR 關聯圖

```
SRD
├── ADR-001（技術棧）
├── ADR-002（架構模式）
└── ADR-003（部署策略）

FRD（如有相關技術決策）
└── ADR-NNN（...）
```

---

## 維護規則

1. 每新增一個 ADR，立即更新本索引
2. ADR 狀態變更時，立即更新本索引
3. 廢棄的 ADR 保留在列表中（標記 Deprecated）
4. 每季度審查 ADR 有效性

**相關文件**：
- [ADR 範本](ADR-TEMPLATE.md)
- [SDD 核心原則](../SDD_Core_Principles.md)
