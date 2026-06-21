# API 向後相容性聲明
# API Backward Compatibility Declaration

**專案**: {PROJECT_NAME}
**版本**: v{NEW_VERSION}（從 v{OLD_VERSION} 升級）
**聲明日期**: YYYY-MM-DD
**負責人**: sd-architect
**適用情境**: Brownfield

---

## 版本升級摘要

| 項目 | 說明 |
|------|------|
| 舊版本 | v{OLD_VERSION} |
| 新版本 | v{NEW_VERSION} |
| 升級原因 | {業務需求描述} |
| 影響 Consumer | {消費此 API 的系統清單} |

---

## Breaking Changes 清單

> ⚠️ **所有 Consumer 必須在升級前確認已了解以下 Breaking Changes**

| # | API 端點 | 變更類型 | 舊行為 | 新行為 | 影響評估 |
|---|---------|---------|--------|--------|---------|
| 1 | `DELETE /api/v1/{path}` | 端點刪除 | 端點存在 | 端點不存在（404）| 高 - 必須遷移 |
| 2 | `POST /api/v1/{path}` | 必填欄位新增 | `email` 選填 | `email` 必填 | 高 - 需更新呼叫端 |
| 3 | `GET /api/v1/{path}` | 回傳格式變更 | 回傳 `data: Object` | 回傳 `data: Array` | 高 - 需更新解析邏輯 |

**Breaking Changes 總數**: {N}

---

## Non-Breaking Changes 清單

| # | API 端點 | 變更類型 | 說明 |
|---|---------|---------|------|
| 1 | `GET /api/v1/{path}` | 新增選填欄位 | 回傳新增 `metadata` 欄位（選填，向後相容）|
| 2 | `POST /api/v2/{path}` | 新增端點 | 全新端點，不影響現有調用 |

---

## 廢棄端點清單（Deprecated Endpoints）

| 端點 | 廢棄版本 | 預計刪除版本 | 替代端點 | Sunset Date |
|------|---------|------------|---------|------------|
| `GET /api/v1/old-path` | v{VERSION} | v{VERSION+2} | `GET /api/v2/new-path` | YYYY-MM-DD |

---

## 遷移指南

### 從 v{OLD} 升級到 v{NEW} 的步驟

1. **更新 Breaking Change 1 - 端點刪除**
   ```
   舊呼叫：DELETE /api/v1/{path}
   新做法：{替代方案說明}
   ```

2. **更新 Breaking Change 2 - 必填欄位**
   ```
   舊請求：{ "name": "value" }
   新請求：{ "name": "value", "email": "required@example.com" }
   ```

---

## Consumer 確認記錄

| Consumer 系統 | 負責人 | 確認日期 | 確認狀態 |
|-------------|-------|---------|---------|
| {系統名稱} | {負責人} | YYYY-MM-DD | ✅ 已確認 / ⏳ 待確認 |

> **🔴 Consumer Side 確認要求**：所有列出的 Consumer 必須在 API 升級前確認已了解影響並完成遷移計畫。

---

**相關文件**:
- [As-Is API Contract](./CONTRACT-{module}-as-is.yaml)
- [To-Be API Contract](./CONTRACT-{module}-v{NEW}.yaml)
- [Gap Analysis](../../docs/04_planning/GAP-ANALYSIS-{feature}.md)
