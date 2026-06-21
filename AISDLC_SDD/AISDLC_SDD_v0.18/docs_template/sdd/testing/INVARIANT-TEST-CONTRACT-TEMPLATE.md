# 不變量測試契約
# Invariant Test Contract

**專案**: {PROJECT_NAME}
**系統**: {SYSTEM_NAME}
**版本**: v1.0
**建立日期**: YYYY-MM-DD
**建立者**: qa-tester（`invariant_test_contract` Skill）
**適用情境**: Refactoring（Stage 1 強制文件）
**關聯文件**: `docs/01_requirements/INVARIANT-SPEC-{system}.md`

---

## 契約目的

> 此文件定義系統重構過程中的測試護欄（Safety Net）。
> 所有列出的不變量測試必須在每個重構步驟後全部通過，才能繼續下一步。

---

## 測試執行要求

| 要求 | 規格 |
|------|------|
| 執行時機 | 每個重構 STEP PR merge 時（CI 自動執行）|
| 通過標準 | 所有 INV 測試 100% 通過（零容忍）|
| 失敗處理 | 立即中斷 Pipeline，禁止 merge，立即修復 |
| Mutation Score | 里程碑時執行，目標 ≥ 80% |

---

## 不變量測試清單

### P0 核心不變量測試

#### INV-001-TEST：{不變量名稱} 測試

**對應不變量**: INV-001（`INVARIANT-SPEC-{system}.md`）  
**測試類型**: 單元測試 / 整合測試 / E2E 測試  
**自動化狀態**: ✅ 已實作 / ⚠️ 需要建立  
**Mutation Test**: YES / NO

**測試規格**:
```
Given {前置條件（精確的系統狀態）}
When  {觸發動作（精確的操作）}
Then  {預期結果（精確的斷言）}
  And {附加驗證條件}
```

**測試實作路徑**:
```
tests/invariants/INV-001-{name}.test.js
describe('INV-001: {不變量名稱}', () => {
  it('should {預期行為描述}', async () => {
    // Given
    // When
    // Then - 精確斷言
  });
});
```

**邊界條件測試**:
```
Given {邊界前置條件 1}
When  {相同觸發動作}
Then  {邊界情況下的預期結果}
```

---

#### INV-002-TEST：{不變量名稱} 測試

（同上格式）

---

### P1 重要業務規則測試

#### INV-003-TEST：{不變量名稱} 測試

（同上格式）

---

## Mutation Test 配置

```yaml
mutation_test_config:
  tool: "stryker（JS/TS）/ pit（Java）/ mutmut（Python）"
  scope:
    include:
      - "src/business-logic/**/*.js"
      - "src/domain/**/*.js"
    exclude:
      - "src/**/*.test.js"
      - "src/infrastructure/**"
  target_score: 80
  mutators: ["ArithmeticOperator", "ConditionalExpression", "LogicalOperator"]
  thresholds:
    high: 80
    low: 60
    break: 50
```

---

## 測試覆蓋追蹤

| INV ID | 不變量名稱 | 測試路徑 | 狀態 | Mutation? |
|--------|-----------|---------|------|-----------|
| INV-001 | {名稱} | `tests/invariants/INV-001.test.js` | ✅ | YES |
| INV-002 | {名稱} | `tests/invariants/INV-002.test.js` | ✅ | YES |
| INV-003 | {名稱} | `tests/invariants/INV-003.test.js` | ⚠️ 需建立 | NO |

**契約完整性**: {N}/{M} 個不變量已有自動化測試

---

## 重構里程碑測試記錄

| 里程碑 | 執行日期 | INV 通過率 | Mutation Score | 狀態 |
|-------|---------|-----------|---------------|------|
| Milestone 1 | YYYY-MM-DD | 100% | {%} | ✅/❌ |
| Milestone 2 | YYYY-MM-DD | 100% | {%} | ✅/❌ |

---

**相關文件**:
- [業務不變量規格](../../01_requirements/INVARIANT-SPEC-{system}.md)
- [Refactoring Plan](../../04_planning/REFACTOR-PLAN-{system}.md)
- [Refactoring CI/CD](../../08_deployment/SDD_REFACTORING_CICD.md)
