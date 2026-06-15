# 程式碼品質基準報告
# Code Quality Baseline Report

**專案**: {PROJECT_NAME}
**系統**: {SYSTEM_NAME}
**快照類型**: Before Refactoring / After Refactoring（擇一）
**版本**: v1.0
**建立日期**: YYYY-MM-DD
**建立者**: code-analyzer（`refactoring_quality_baseline` Skill）
**適用情境**: Refactoring（Stage 0 必要文件）

---

## 快照摘要

| 指標 | 數值 | 閾值 | 狀態 |
|------|------|------|------|
| 平均 Cyclomatic Complexity | {數值} | ≤ 10 | ✅/⚠️/❌ |
| 高複雜度函數數量（> 15）| {數值} | ≤ 5 | ✅/⚠️/❌ |
| 模組耦合度（平均）| {數值} | ≤ 5 | ✅/⚠️/❌ |
| Line Coverage | {%} | ≥ 60% | ✅/⚠️/❌ |
| Branch Coverage | {%} | ≥ 50% | ✅/⚠️/❌ |
| Code Duplication Rate | {%} | ≤ 10% | ✅/⚠️/❌ |
| Technical Debt Ratio | {%} | ≤ 5% | ✅/⚠️/❌ |

---

## 1. Cyclomatic Complexity（程式碼複雜度）

**工具**: ESLint complexity rule / SonarQube  
**整體平均**: {數值}

### Top 10 高複雜度函數

| # | 函數名稱 | 複雜度 | 路徑 | 建議 |
|---|---------|--------|------|------|
| 1 | `{functionName}` | {數值} | `src/path/file.js:L{行號}` | {重構建議} |
| 2 | `{functionName}` | {數值} | `src/path/file.js:L{行號}` | {重構建議} |

---

## 2. Module Coupling（模組耦合度）

**工具**: dependency-cruiser

### 高耦合模組清單（Ce + Ca > 10）

| 模組名稱 | 進入耦合 Ce | 離開耦合 Ca | 不穩定度 I | 說明 |
|---------|-----------|-----------|-----------|------|
| `{ModuleName}` | {數值} | {數值} | {數值} | {說明} |

### 循環依賴清單

| # | 循環路徑 | 嚴重程度 |
|---|---------|---------|
| 1 | `A → B → C → A` | 高 |

---

## 3. Test Coverage（測試覆蓋率）

**工具**: Istanbul（nyc）/ JaCoCo / Coverage.py

### 整體覆蓋率

| 指標 | 數值 | 狀態 |
|------|------|------|
| Lines | {%} | ✅/⚠️/❌ |
| Branches | {%} | ✅/⚠️/❌ |
| Functions | {%} | ✅/⚠️/❌ |
| Statements | {%} | ✅/⚠️/❌ |

### 低覆蓋率模組清單（Line < 60%）

| 模組 | Line% | Branch% | 優先級 |
|------|-------|---------|--------|
| `{ModuleName}` | {%} | {%} | P0/P1/P2 |

---

## 4. Code Duplication（程式碼重複率）

**工具**: jscpd / SonarQube  
**整體重複率**: {%}

### 重複程式碼位置清單（> 50 tokens）

| # | 重複片段 | 位置 1 | 位置 2 | 行數 |
|---|---------|-------|-------|------|
| 1 | {描述} | `src/a.js:L10-30` | `src/b.js:L5-25` | 20 行 |

---

## 5. Technical Debt Ratio（技術債比率）

**工具**: SonarQube  
**整體 TDR**: {%}（≤ 5% 為良好）

| 類別 | TDR% | 修復時間估算 |
|------|------|------------|
| 架構 | {%} | {N} days |
| 程式碼 | {%} | {N} days |
| 安全 | {%} | {N} days |
| 測試 | {%} | {N} days |
| 文件 | {%} | {N} days |

---

## Before vs After 比較（重構後填寫）

| 指標 | Before | After | 改善量（Δ）| 達標？ |
|------|--------|-------|-----------|--------|
| 平均 Complexity | {數值} | {數值} | {Δ} | ✅/❌ |
| Line Coverage | {%} | {%} | {Δ%} | ✅/❌ |
| TDR | {%} | {%} | {Δ%} | ✅/❌ |
| Coupling | {數值} | {數值} | {Δ} | ✅/❌ |

**改善目標**: 重構後 Complexity 降低 ≥ 20%，Coverage 不低於重構前

---

**相關文件**:
- [Refactoring SDD 強化規範](../../scenarios/refactoring/SDD_REFACTORING_ENHANCEMENT.md)
- [Before Architecture](../../docs/02_architecture/BEFORE-ARCH-{system}.md)
- [After Architecture](../../docs/02_architecture/AFTER-ARCH-{system}.md)
