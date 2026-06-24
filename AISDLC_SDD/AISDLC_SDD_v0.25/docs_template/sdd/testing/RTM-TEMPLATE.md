# 需求追溯矩陣（Requirements Traceability Matrix）
# RTM-TEMPLATE

**專案**: {PROJECT_NAME}
**版本**: v1.0
**建立日期**: YYYY-MM-DD
**建立者**: QA Lead / SA Analyst
**觸發 Skill**: `traceability_matrix`

---

## 使用說明

本範本使用 `traceability_matrix` Skill 生成，建立從業務需求到測試案例的完整追溯鏈。

**觸發時機**：
- Stage 3：SA 完成 FRD 後
- Stage 5：SD 完成 SRD 後
- Stage 6：QA 完成測試計畫後
- 任何需求變更後

---

## 追溯矩陣

| EPIC | Feature | User Story | AC | AT | API | NFR | 狀態 | 備註 |
|------|---------|-----------|-----|-----|-----|-----|------|------|
| EPIC-001 | F-001 | US-001 | AC-001-1 | AT-001-1-1 | API-001 | NFR-001 | ✅ 已覆蓋 | |
| EPIC-001 | F-001 | US-001 | AC-001-2 | AT-001-1-2 | API-001 | - | ✅ 已覆蓋 | |
| EPIC-001 | F-002 | US-002 | AC-002-1 | AT-002-1-1 | API-002 | NFR-002 | ⚠️ 部分覆蓋 | 缺少邊界測試 |
| EPIC-002 | F-003 | US-003 | AC-003-1 | - | API-003 | - | ❌ 未覆蓋 | 需補充測試 |

**狀態說明**：
- ✅ 已覆蓋：所有 AC 都有對應 AT
- ⚠️ 部分覆蓋：部分 AC 缺少 AT
- ❌ 未覆蓋：沒有任何 AT 對應

---

## 覆蓋率統計

| 指標 | 數量 | 百分比 |
|------|------|--------|
| 總 User Stories | N | 100% |
| 已覆蓋 US | N | X% |
| 總 AC 數量 | N | 100% |
| 已覆蓋 AC | N | X% |
| 總 AT 數量 | N | - |

---

## 未覆蓋項目清單（需補充）

| ID | 類型 | 描述 | 優先級 | 負責人 |
|----|------|------|--------|--------|
| US-XXX | User Story | {描述} | High | QA |

---

## 相關文件

- FRD：`docs/01_requirements/`
- SRD：`docs/02_architecture/`
- 測試計畫：`docs/03_testing/`
- API Spec：`docs/02_architecture/api/`

---

**最後更新**: YYYY-MM-DD
**Spec Gate**: 🔷 SCG-4 Test Strategy Gate
