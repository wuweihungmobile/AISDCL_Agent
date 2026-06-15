# Refactoring SDD CI/CD Pipeline 規格
# SDD Refactoring CI/CD Enhancement

**版本**: v1.0
**建立日期**: 2026-04-12
**適用情境**: Refactoring（系統重構）
**前置條件**: Phase 01 SDD_CICD_BASE_LAYER.md 已定義

---

## 🏗️ Refactoring Pipeline 架構

```
Build → DocLint → SpecTrace → Unit Test(Invariant) → SAST → MutationTest → ArchDiff → Notify
          ↑            ↑              ↑                          ↑              ↑
    （Phase 01） （Phase 01）  （重構核心驗證）           （Phase 03 新增）   （Phase 03 新增）
```

**關鍵原則**：每個重構 STEP 完成後，必須執行完整 Pipeline 才能繼續下一個 STEP。

---

## 📋 Refactoring SDD Pipeline 步驟

### 3.7.1 DocLint + SpecTrace（Before/After 規格一致性）

```yaml
refactoring_doclint:
  name: "DocLint - Refactoring Spec Completeness"
  trigger: "每個重構 STEP 的 PR merge 時"
  checks:
    before_arch_required:
      - "docs/02_architecture/BEFORE-ARCH-{system}.md 存在"
      - "docs/06_quality/CODE-QUALITY-BASELINE.md 存在（Before 版本）"
      - "docs/01_requirements/INVARIANT-SPEC-{system}.md 存在"
    after_arch_required:
      - "docs/02_architecture/AFTER-ARCH-{system}.md 存在（Stage 2 後）"
      - "docs/03_testing/contracts/INVARIANT-TEST-CONTRACT.md 存在"
      - "docs/04_planning/REFACTOR-PLAN-{system}.md 存在"
    adr_required:
      - "docs/02_architecture/adr/ADR-REFACTOR-*.md 存在（每個重構決策）"
  fail_on_error: true

refactoring_spectrace:
  name: "SpecTrace - Before/After Spec Consistency"
  checks:
    - "每個 BEFORE-ARCH 描述的元件在 AFTER-ARCH 中有對應處理（保留/修改/刪除）"
    - "每個 ADR-REFACTOR-*.md 在 REFACTOR-PLAN 中有對應 STEP"
    - "所有 INV-XXX 都在 INVARIANT-TEST-CONTRACT 中有自動化測試"
  fail_on_error: true
```

### 3.7.2 Unit Test（不變量測試 100% 必須通過）

```yaml
invariant_unit_test:
  name: "Invariant Tests - Must Pass 100%"
  trigger: "每個重構 STEP PR 時（自動執行）"
  scope: "docs/03_testing/contracts/INVARIANT-TEST-CONTRACT.md 中的所有 INV-XXX"
  pass_criteria:
    - "INV Test 通過率 100%（zero tolerance）"
    - "任何 INV Test 失敗 → Pipeline 中斷 → 禁止 merge"
  fail_on_error: true
  note: "這是重構 Pipeline 的核心防護網，不可降低標準"
```

### 3.7.3 SAST（靜態安全掃描）

```yaml
sast:
  note: "靜態安全掃描維持原有設定"
  refactoring_addition: "重構後必須確認 SAST 結果不比重構前更差（不可引入新安全問題）"
```

### 3.7.4 Mutation Test（SDD 強化）

```yaml
mutation_test:
  name: "Mutation Test - Business Logic Integrity"
  trigger: "每個重構里程碑（非每個 STEP，避免 CI 時間過長）"
  tools:
    javascript: "Stryker（npm run stryker）"
    java: "PIT（mvn pitest:mutationCoverage）"
    python: "mutmut（mutmut run）"
    csharp: "Stryker.NET"
  scope: "INVARIANT-TEST-CONTRACT 覆蓋的業務邏輯函數（非全量）"
  pass_criteria:
    target_score: "Mutation Score ≥ 80%"
    definition: "80% 的 Mutation（人工植入的 Bug）被不變量測試偵測到"
  fail_on_error: true
  output: "build/reports/verification/MutationTest-{milestone}-{date}.md"
  note: "Mutation Score < 80% 表示不變量測試不夠強，重構風險高"
```

### 3.7.5 ArchDiff（Before/After 架構差異自動分析）

```yaml
arch_diff:
  name: "Architecture Diff - Before vs After"
  trigger: "每個重構里程碑完成後"
  analysis:
    dependency_diff:
      tool: "dependency-cruiser"
      compare: "Before Dependency Graph vs 當前 Dependency Graph"
      metrics:
        - "耦合度改善量（Δ Coupling Score）"
        - "循環依賴消除數量"
        - "模組邊界清晰度改善"
    complexity_diff:
      tool: "ESLint complexity / SonarQube"
      compare: "CODE-QUALITY-BASELINE.md (Before) vs 當前量化結果"
      metrics:
        - "平均 Cyclomatic Complexity 變化（期望：降低）"
        - "高複雜度函數數量變化"
    coverage_diff:
      tool: "Istanbul / JaCoCo"
      compare: "Before Coverage vs 當前 Coverage"
      requirement: "重構後測試覆蓋率不得低於重構前"
  output: "build/reports/verification/ArchDiff-{milestone}-{date}.md"
  fail_on_error: false
  milestone_gate: "ArchDiff 報告必須由 sd-architect + Human 審閱後才能關閉里程碑"
```

### 3.7.6 Notify（維持不變）

```yaml
notify:
  note: "標準 Slack/Teams 通知無變化"
  refactoring_addition: "里程碑完成通知加入 ArchDiff 報告連結"
```

---

## 🚦 重構 Pipeline 決策流程

```
每個 STEP PR merge 前：
  ├── Invariant Test 100% 通過？
  │   ├── YES → 繼續
  │   └── NO → 🔴 禁止 merge，立即修復
  ├── DocLint 通過？
  │   ├── YES → 繼續
  │   └── NO → 修正文件後重試
  └── SAST 無新問題？
      ├── YES → PR merge 通過
      └── NO → 評估是否為重構引入的安全問題

每個里程碑最後一個 STEP 完成後（額外執行）：
  ├── Mutation Test ≥ 80%？
  │   ├── YES → 繼續
  │   └── NO → 補充不變量測試後重跑
  ├── ArchDiff 報告審閱？
  │   ├── Human 確認 → 里程碑關閉
  │   └── 有問題 → 修正後重新確認
  └── 繼續下一個里程碑？
      └── 🔴 Human 確認（Go/No-Go）
```

---

## 🔗 相關文件

- [SDD CI/CD 基礎層](SDD_CICD_BASE_LAYER.md)
- [Refactoring SDD 強化規範](../../AISDLC_v0.09/scenarios/refactoring/SDD_REFACTORING_ENHANCEMENT.md)
