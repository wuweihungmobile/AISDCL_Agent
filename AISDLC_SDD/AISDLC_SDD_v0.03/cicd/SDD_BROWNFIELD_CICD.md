# Brownfield SDD CI/CD Pipeline 規格
# SDD Brownfield CI/CD Enhancement

**版本**: v1.0
**建立日期**: 2026-04-12
**適用情境**: Brownfield（舊專案維護）
**前置條件**: Phase 01 SDD_CICD_BASE_LAYER.md 已定義

---

## 🏗️ Brownfield L0 基礎層（SDD 強化版）

### Pipeline 架構

```
Build → Unit Test → Lint → DocLint → SpecTrace → SAST → Regression → CompatCheck → Deploy
                              ↑           ↑                   ↑              ↑
                    （Phase 01）    （Phase 01）        （SDD 強化）     （Phase 03 新增）
```

---

## 📋 Brownfield SDD Pipeline 步驟

### 3.3.1 DocLint + SpecTrace（As-Is 規格完整性）

```yaml
brownfield_doclint:
  name: "DocLint - As-Is Spec Completeness"
  trigger: "PR 到 develop/main 分支時"
  checks:
    as_is_spec:
      - "docs/01_requirements/AS-IS-FRD-*.md 存在（有任何 Brownfield 功能時）"
      - "docs/02_architecture/AS-IS-SRD-*.md 存在"
      - "docs/02_architecture/adr/ 有 ADR-AS-IS-*.md"
    to_be_spec:
      - "docs/02_architecture/TO-BE-SRD-*.md 存在（有新功能時）"
      - "docs/04_planning/GAP-ANALYSIS-*.md 存在"
    general:
      - "所有 .md 文件通過 markdownlint"
      - "所有內部連結有效"
  fail_on_error: true

brownfield_spectrace:
  name: "SpecTrace - Brownfield Impact Matrix"
  trigger: "docs/03_testing/RTM-*.md 有變更時"
  checks:
    - "As-Is FRD 的 US 都在 RTM 中（無遺漏）"
    - "Gap Analysis 中的受影響 US 都有對應 AT"
    - "回歸測試範圍基於 RTM Impact Matrix（非人工判斷）"
  fail_on_error: false
  output: "build/reports/verification/Brownfield-SpecTrace-{date}.md"
```

### 3.3.2 Unit Test + Build（維持不變）

```yaml
unit_test:
  note: "Unit Test + Build Check 維持原有設定，無 Brownfield 特殊調整"
  additional: "建議確保 As-Is 測試在修改前全部通過（作為基準）"
```

### 3.3.3 SAST（維持不變）

```yaml
sast:
  note: "靜態安全掃描維持原有設定"
  brownfield_addition: "Brownfield 建議額外執行 dependency audit（npm audit / OWASP Dependency-Check）"
```

### 3.3.4 Regression（SDD 強化版）

```yaml
brownfield_regression:
  name: "RTM-Driven Regression Test"
  trigger: "每次 PR merge 時（非 feature branch）"
  sdd_requirement:
    - "回歸測試範圍必須由 RTM Impact Analysis 決定"
    - "從 GAP-ANALYSIS-{feature}.md 提取受影響 US 清單"
    - "從 RTM 查找受影響 US 的 AT 清單"
    - "執行：受影響 AT + 核心路徑 AT（Core Path AT）"
  anti_pattern: "❌ 禁止人工決定回歸範圍（風險：遺漏隱性影響）"
  output: "build/reports/verification/Regression-Coverage-{date}.md"
  fail_on_error: true
```

### 3.3.5 CompatCheck（Breaking Changes 自動驗證）

```yaml
compat_check:
  name: "API Backward Compatibility Check"
  trigger: "docs/02_architecture/api/ 有變更時"
  tool: "openapi-diff / breaking-change-detector"
  checks:
    - "比對 As-Is API Spec 與 To-Be API Spec"
    - "偵測所有 Breaking Changes（端點刪除、必填欄位新增、型別變更）"
    - "驗證 Breaking Changes 是否已在 API-COMPAT-{version}.md 中聲明"
    - "驗證 Consumer Side 是否已確認（requires: consumer_sign_off: true）"
  fail_on_error: true
  output: "build/reports/verification/APICompat-{date}.md"
  breaking_change_rules:
    - "刪除端點 → Breaking（除非有 deprecation period）"
    - "新增必填欄位 → Breaking"
    - "修改回傳格式 → Breaking"
    - "修改認證機制 → Breaking"
    - "新增選填欄位 → Non-Breaking"
    - "新增端點 → Non-Breaking"
```

### 3.3.6 Notify（維持不變）

```yaml
notify:
  note: "標準 Slack/Teams 通知無變化"
  brownfield_addition: "Brownfield 建議加入 API Breaking Change 特別警告通知"
```

---

## 🔗 相關文件

- [SDD CI/CD 基礎層](SDD_CICD_BASE_LAYER.md)
- [Brownfield SDD 強化規範](../../AISDLC_v0.09/scenarios/brownfield/SDD_BROWNFIELD_ENHANCEMENT.md)
