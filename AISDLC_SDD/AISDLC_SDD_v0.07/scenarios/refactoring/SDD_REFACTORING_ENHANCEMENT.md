# Refactoring 情境 SDD 強化規範
# SDD Refactoring Scenario Enhancement

**版本**: v1.0
**建立日期**: 2026-04-12
**適用情境**: Refactoring（系統重構）
**前置條件**: Phase 01 SDD_CICD_BASE_LAYER.md 已定義

---

## 🎯 核心原則

> **「重構不是盲目修改程式碼，而是依照目標規格重新實現相同功能」**

**重構前 SDD 必備四件事**：
1. **Before Architecture Spec**：重構前的完整架構文件
2. **Business Invariants**：明確定義不可改變的業務行為
3. **Refactoring Plan as Spec**：重構計畫本身即是規格文件
4. **After Architecture Spec**：重構後的目標架構文件

---

## 🏗️ SDD 強化版 Refactoring 流程

### Stage 0：重構準備（3.5.1-3.5.3）

```
Stage 0: 重構準備（SDD 強制）
  ├── code-analyzer: 程式碼品質量化（複雜度/耦合度/覆蓋率）→ CODE-QUALITY-BASELINE.md
  ├── sd-architect: Before Architecture Spec（當前架構文件化）
  ├── sd-architect: Before C4 圖（Context L1 + Container L2 強制）
  └── 🔴 Human: 確認重構範圍與目標（什麼要改、什麼不能改）
```

**3.5.1 Before Architecture Spec（重構前必須完整）**:
```yaml
before_arch_spec:
  file: "docs/02_architecture/BEFORE-ARCH-{system}.md"
  mandatory_content:
    - "Before C4 Context 圖（L1）"
    - "Before C4 Container 圖（L2）"
    - "當前技術棧（含版本號）"
    - "當前模組依賴關係"
    - "已知設計問題（Why Refactoring）"
  quality_gate: "SCG-0：Before Arch 文件化完成 → Human 確認"
  anti_pattern: "❌ 不可在 Before Arch 未確認前開始任何重構"
```

**3.5.2 Before C4 圖（Context + Container 強制）**:
```yaml
before_c4:
  format: "Mermaid C4Context + C4Container diagrams"
  embedded_in: "docs/02_architecture/BEFORE-ARCH-{system}.md"
  requirement: "必須反映重構前的實際部署架構（由 dev-senior 確認準確性）"
```

**3.5.3 程式碼品質基準報告（量化指標）**:
```yaml
code_quality_baseline:
  file: "docs/06_quality/CODE-QUALITY-BASELINE.md"
  metrics:
    - "Cyclomatic Complexity（整體平均 + Top 10 高複雜度函數）"
    - "Module Coupling（高耦合模組清單）"
    - "Test Coverage（Line/Branch/Function %）"
    - "Code Duplication（重複率 %）"
    - "Technical Debt Ratio（TDR%）"
  snapshot: "重構前建立 Before Baseline，重構後建立 After Baseline"
  tool: "code-analyzer（SonarQube / ESLint / Istanbul）"
```

---

### Stage 1：業務不變量規格（3.5.4-3.5.5）

**3.5.4 Business Invariants Spec（業務不變量清單）**:
```yaml
invariant_spec:
  file: "docs/01_requirements/INVARIANT-SPEC-{system}.md"
  definition: "重構前後必須完全一致的業務行為"
  format:
    invariant_record:
      id: "INV-{NNN}"
      name: "不變量名稱"
      rule: "業務規則描述（必須精確、可測試）"
      examples: ["正例（符合此規則的輸入/輸出）", "反例（違反此規則的案例）"]
      verification: "如何驗證此不變量（測試策略）"
  sources:
    - "現有 FRD 中的業務規則"
    - "現有測試案例中的斷言"
    - "業務人員訪談"
    - "合規要求（不可改變的法規邏輯）"
  human_confirmation: "🔴 Human（業務人員）: 不變量清單確認"
  quality_gate: "SCG-1：不變量規格 Human 凍結"
```

**3.5.5 Invariant Test Contract（不變量測試規格）**:
```yaml
invariant_test_contract:
  file: "docs/03_testing/contracts/INVARIANT-TEST-CONTRACT.md"
  requirement: "每個 INV-XXX 必須有對應的自動化測試"
  pass_criteria:
    - "重構前：所有不變量測試 100% 通過（基準確立）"
    - "重構中：每個原子步驟後執行全套不變量測試"
    - "重構後：所有不變量測試 100% 通過（驗收）"
  mutation_test:
    tool: "Stryker（JS/TS）/ PIT（Java）/ mutmut（Python）"
    target_score: "Mutation Score ≥ 80%"
    scope: "Invariant Test 覆蓋的業務邏輯函數"
  template: "docs/03_testing/contracts/INVARIANT-TEST-CONTRACT-TEMPLATE.md"
```

---

### Stage 2：重構目標規格（3.5.6-3.5.8）

**3.5.6 After Architecture Spec（目標架構文件）**:
```yaml
after_arch_spec:
  file: "docs/02_architecture/AFTER-ARCH-{system}.md"
  mandatory_content:
    - "After C4 Context 圖（L1）"
    - "After C4 Container 圖（L2）"
    - "目標技術棧（含版本號）"
    - "模組依賴改善後的狀態"
    - "Before vs After 對照表（哪些改了、哪些沒改）"
  quality_gate: "SCG-2：After Arch 規格凍結 → Human 確認"
```

**3.5.7 After C4 圖（目標 C4）**:
```yaml
after_c4:
  format: "Mermaid C4Context + C4Container diagrams"
  embedded_in: "docs/02_architecture/AFTER-ARCH-{system}.md"
  comparison: "After C4 必須與 Before C4 放在同一文件的相鄰位置，方便對比"
```

**3.5.8 重構 ADR（Before/Decision/After 格式）**:
```yaml
refactoring_adr:
  file: "docs/02_architecture/adr/ADR-REFACTOR-{NNN}-{decision}.md"
  special_format:
    before_state: "重構前的架構狀態（現況問題）"
    decision: "重構決策（做什麼改變）"
    after_state: "重構後的目標架構狀態"
    rationale: "為什麼這樣重構（解決了什麼問題）"
    invariants_preserved: "確認哪些業務不變量不受影響"
    risk: "重構風險與緩解措施"
  requirement: "每個架構層面的重構決策都需要獨立 ADR"
  examples: ["模組拆分 ADR", "設計模式替換 ADR", "依賴方向調整 ADR"]
```

---

### Stage 3：重構計畫即規格（3.5.9）

**3.5.9 Refactoring Plan as Spec**:
```yaml
refactoring_plan:
  file: "docs/04_planning/REFACTOR-PLAN-{system}.md"
  sdd_principle: "重構計畫本身就是規格文件，每個步驟必須可驗證"
  plan_structure:
    strategy:
      options:
        - "Strangler Fig Pattern（逐步替換，舊系統漸進廢棄）"
        - "Branch by Abstraction（先抽象化，再替換實作）"
        - "Parallel Run（新舊並行，驗證後切換）"
        - "Big Bang（一次性替換，高風險，需強大測試保障）"
      selection_criteria: "選擇策略的理由（依據風險評估）"
    steps:
      per_step:
        id: "STEP-{NNN}"
        description: "此步驟做什麼（原子操作）"
        before_state: "執行前的系統狀態"
        after_state: "執行後的系統狀態"
        invariant_tests: "此步驟後必須通過的不變量測試（INV-XXX 清單）"
        rollback_plan: "若此步驟失敗，如何回滾"
        estimated_size: "Story Points"
    milestone_gates:
      - "每個里程碑（5-10 個 STEP）必須有 Human 確認"
      - "里程碑通過條件：所有不變量測試通過 + Human 確認"
  requirement: "每個 STEP 必須是「原子操作」- 單一職責，易於驗證"
```

**3.5.10 每個重構步驟後更新 After Architecture 進度**:
```yaml
progress_tracking:
  requirement: "每個 STEP-{NNN} 完成後，更新 AFTER-ARCH 進度文件"
  update_content:
    - "標記已完成的 STEP（✅）"
    - "更新當前架構狀態（Intermediate State C4）"
    - "記錄實際執行與計畫的差異"
  output: "AFTER-ARCH-{system}.md 的「重構進度」章節"
```

---

## 🔍 3.8 產出物審查工作流

### 3.8.1 Before Architecture 審查

**參與者**: sd-architect（主持）+ dev-senior
**觸發時機**: Stage 0 完成後（SCG-0 前）
**審查項目**:
```yaml
before_arch_review:
  accuracy_checks:
    - "Before C4 圖是否反映實際生產架構？"
    - "程式碼品質基準數字是否由工具生成（非估算）？"
    - "技術棧版本號是否準確？"
    - "已知設計問題清單是否完整？"
  human_confirmation: "🔴 dev-senior + Human 確認現況準確"
```

### 3.8.2 業務不變量審查

**參與者**: sa-analyst（主持）+ ba + qa-tester
**觸發時機**: Stage 1 完成後（SCG-1 前）
**審查項目**:
```yaml
invariant_review:
  completeness_checks:
    - "核心業務流程（Happy Path）是否全部列為不變量？"
    - "財務計算、合規邏輯是否標記為不變量？"
    - "每個不變量是否可自動化測試？"
    - "是否有遺漏的隱性業務規則？"
  zero_tolerance: "任何業務不變量的遺漏都可能導致重構引入 Bug"
  human_confirmation: "🔴 業務人員（ba/PM）必須確認不變量清單完整"
```

### 3.8.3 After Architecture 審查

**參與者**: sd-architect（主持）+ dev-senior + dev-developer
**觸發時機**: Stage 2 完成後（SCG-2 前）
**審查項目**:
```yaml
after_arch_review:
  feasibility_checks:
    - "After C4 圖是否技術可行？"
    - "重構 ADR 是否每個決策都有充分理由？"
    - "Before → After 對照表是否清晰？"
    - "依賴方向改善是否真實解決原有問題？"
  spec_gate: "🔷 SCG-2 通過"
  human_confirmation: "🔴 Human: After 規格凍結"
```

### 3.8.4 重構計畫審查

**參與者**: sd-architect（主持）+ dev-senior + qa-tester
**觸發時機**: Stage 3 完成後
**審查項目**:
```yaml
refactoring_plan_review:
  completeness_checks:
    - "所有 STEP 是否為原子操作（單一職責）？"
    - "每個 STEP 是否有明確的 Rollback Plan？"
    - "不變量測試是否覆蓋所有 STEP 的後置狀態？"
    - "里程碑劃分是否合理（風險可控）？"
  strategy_validation:
    - "選擇的重構策略（Strangler Fig / Branch by Abstraction 等）是否合適？"
    - "高風險 STEP 是否有額外保護措施？"
  human_confirmation: "🔴 Human: 重構計畫確認"
```

### 3.8.5 每個重構里程碑驗證

**參與者**: qa-tester（自動化）+ Human（確認）
**觸發時機**: 每個里程碑的最後一個 STEP 完成後
**審查項目**:
```yaml
milestone_verification:
  automated_checks:
    - "所有不變量測試通過率 100%"
    - "Mutation Score ≥ 80%（INV 相關函數）"
    - "Before Baseline vs 當前 Baseline 改善量"
  human_checks:
    - "重構進度是否符合計畫？"
    - "是否有意外的行為變化？"
    - "是否繼續下一個里程碑？"
  go_no_go: "不變量測試未全部通過 → 禁止進入下一里程碑"
```

---

## 📊 Refactoring SDD 健康度指標

| 指標 | 計算方式 | 目標 |
|------|---------|------|
| 不變量覆蓋率 | 有自動化測試的 INV / 總 INV | 100% |
| Mutation Score | Mutation 被殺死數 / 總 Mutation 數 | ≥ 80% |
| 架構改善率 | After Complexity / Before Complexity | < 0.8（降低 20%+）|
| 重構計畫完整性 | 有 Rollback Plan 的 STEP / 總 STEP | 100% |

---

## 🔗 相關文件

- [SDD CI/CD Refactoring](../../../docs/08_deployment/SDD_REFACTORING_CICD.md)
- [SDD 核心原則](../../../docs/02_architecture/SDD_Core_Principles.md)
- [ADR 範本](../../../docs/02_architecture/adr/ADR-TEMPLATE.md)
- [Phase 03 執行藍圖](../../../docs/04_planning/AISDLC_TO_SDD_Planning_Phase_03.md)
