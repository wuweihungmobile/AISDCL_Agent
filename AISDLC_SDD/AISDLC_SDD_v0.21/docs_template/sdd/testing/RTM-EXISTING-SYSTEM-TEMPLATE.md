# 既有系統需求追溯矩陣（逆向提取版）
# RTM for Existing System - Reverse Extraction

**專案**: {PROJECT_NAME}
**版本**: v1.0
**建立日期**: YYYY-MM-DD
**建立者**: sa-analyst（`reverse_rtm_extraction` Skill）
**適用情境**: Documentation（既有系統）

---

## 使用說明

本範本用於 Documentation 情境，從現有 FRD/SRD/代碼逆向提取需求追溯矩陣。
使用 `sa-analyst` 的 `reverse_rtm_extraction` Skill 執行。

### 逆向提取步驟

1. 掃描現有 FRD → 提取 User Story 列表
2. 識別並補充缺失的 AC
3. 從 SRD 提取 NFR 映射
4. 從現有測試文件提取 AT（如有）
5. 標記缺口（無 AC/AT 的 US）

---

## 追溯矩陣

| EPIC | Feature | User Story | AC | AT | API | NFR | 狀態 | 備註 |
|------|---------|-----------|-----|-----|-----|-----|------|------|
| EPIC-001 | F-001 | US-001 | AC-001-1 | AT-001-1-1 | API-001 | NFR-001 | ✅ 已覆蓋 | |
| EPIC-001 | F-001 | US-001 | AC-001-2 | _(待補充)_ | - | - | ⚠️ 缺 AT | 逆向提取缺口 |
| EPIC-002 | F-002 | US-002 | _(待補充)_ | - | - | - | ❌ 缺 AC | 需訪談確認 |

**狀態說明**：
- ✅ 已覆蓋：完整追溯鏈
- ⚠️ 部分覆蓋：缺少 AT 或 AC
- ❌ 缺口：缺少 AC 或更上層規格
- 🔍 待確認：需與業務確認

---

## 覆蓋率統計

| 指標 | 總數 | 已覆蓋 | 缺口數 | 覆蓋率 |
|------|------|--------|--------|--------|
| User Stories | N | N | N | X% |
| AC 總數 | N | N | N | X% |
| AT 總數 | N | N | N | X% |
| NFR 已對應 | N | N | N | X% |

---

## 缺口清單（需補充）

### P0 缺口（核心功能缺失 AC/AT）

| ID | 類型 | 描述 | 優先級 | 補充負責人 |
|----|------|------|--------|-----------|
| US-XXX | 缺 AC | {功能描述} | P0 | sa-analyst |
| AC-XXX-1 | 缺 AT | {AC 描述} | P0 | qa-tester |

### P1 缺口（次要功能）

| ID | 類型 | 描述 | 優先級 | 補充負責人 |
|----|------|------|--------|-----------|

---

## 逆向提取來源

| 來源文件 | 路徑 | 提取時間 |
|---------|------|---------|
| FRD | `docs/01_requirements/` | YYYY-MM-DD |
| SRD | `docs/02_architecture/` | YYYY-MM-DD |
| 測試計畫 | `docs/03_testing/` | YYYY-MM-DD |
| 代碼掃描 | `src/` | YYYY-MM-DD |

---

**相關文件**：
- [RTM 標準範本](RTM-TEMPLATE.md)
- [SDD 符合度審計](../02_architecture/SDD-COMPLIANCE-AUDIT-TEMPLATE.md)
