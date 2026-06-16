# SDD Testing CI/CD Pipeline 規格
# SDD Testing Scenario CI/CD Specification

**版本**: v1.0
**建立日期**: 2026-04-13
**文件類型**: 部署規格（Deployment Specification）
**所屬分類**: `AISDLC_SDD_v0.01/cicd/`
**Spec Gate**: 🔷 SCG-4 Test Strategy Gate
**對應 Phase**: Phase 05 — 情境八：Testing（測試與QA）

---

## 🎯 目的

定義 SDD Testing 情境的 CI/CD Pipeline 規格，強制在 Pipeline 中實現「測試即規格」原則：
- 測試策略規格（Test Strategy Spec）先於程式碼提交驗證
- 測試金字塔比例自動監控
- RTM Coverage Report 自動生成
- Quality Gate 量化閾值阻擋不達標的合併

---

## 🏗️ Pipeline 架構

```
┌─────────────────────────────────────────────────────────┐
│            SDD Testing CI/CD Pipeline                    │
├─────────────────────────────────────────────────────────┤
│  L0: DocLint + TestSpec-Validate                         │
│   ↓                                                      │
│  L1: Unit Test（基於 Test Pyramid Spec）                 │
│   ↓                                                      │
│  SAST: 靜態安全掃描（Security Unit Test）                │
│   ↓                                                      │
│  L2 Full:                                                │
│    ├── Contract Tests（取代 Mock Integration）           │
│    ├── Integration Tests（基於 Test Pyramid Spec）       │
│    ├── E2E Tests（覆蓋關鍵使用者旅程）                   │
│    └── RTM Coverage Report 自動生成                      │
│   ↓                                                      │
│  🔴 Quality Gate: 覆蓋率 < 目標時自動失敗               │
│   ↓                                                      │
│  🔔 Notify: Standard                                     │
└─────────────────────────────────────────────────────────┘
```

---

## 📋 各階段詳細規格

### L0: DocLint + TestSpec-Validate（文件完整性驗證）

**觸發條件**：每次 PR / Merge

**驗證規則**：

```yaml
testspec_validate_rules:
  test_strategy_spec:
    required: true
    path: "docs/03_testing/TEST-STRATEGY-*.md"
    checks:
      - "測試金字塔比例已定義（Unit/Integration/E2E 百分比）"
      - "覆蓋率 SLA 已設定（各層目標數值）"
      - "測試工具已選型（有對應 ADR 參考）"
      - "CI 整合規格已描述"
      - "Quality Gate 閾值已定義（Pass/Fail 標準）"

  test_contract_spec:
    required_when: "有 API 整合點"
    path: "docs/03_testing/contracts/TCS-*.md"
    checks:
      - "每個 API 整合點有對應 Contract Test"
      - "Consumer/Provider 角色已定義"

  rtm_completeness:
    checks:
      - "RTM 中 AC → AT 映射覆蓋率 ≥ 90%"
      - "所有 P0 功能有對應 AT"

fail_policy:
  - "Test Strategy Spec 缺失 → 阻擋 PR（SCG-4 Gate）"
  - "RTM AT 覆蓋率 < 90% → 警告（不阻擋）"
```

---

### L1: Unit Test（單元測試執行）

**SDD 強化規格**：

```yaml
unit_test_spec:
  based_on: "docs/03_testing/TEST-STRATEGY-{project}.md 的測試金字塔規格"
  
  coverage_requirements:
    overall_line_coverage: ">= 80%"  # 從 Test Strategy Spec 取得
    branch_coverage: ">= 70%"
    business_logic_coverage: ">= 90%"  # 核心業務邏輯更高要求

  execution:
    parallel: true
    timeout: "10 minutes"
    retry_on_failure: 1

  quality_gate:
    fail_when:
      - "overall_line_coverage < 80%"
      - "any critical business logic function uncovered"
      - "unit test execution time > 10 minutes"
```

---

### SAST: 靜態安全掃描

```yaml
sast_spec:
  tools:
    - name: "SonarQube / Semgrep"
      ruleset: "OWASP Top 10 + Security Unit Tests"
      
  gates:
    fail_when:
      - "Critical 漏洞 > 0"
      - "High 漏洞 > 0（Security 相關）"
    warn_when:
      - "Medium 漏洞 > 0（記錄至 Tech Debt）"
```

---

### L2 Full: 完整測試套件（SDD 強化版）

```yaml
l2_full_spec:
  trigger: "Merge to main / Release branch"

  contract_tests:
    description: "取代所有 Mock-Based Integration Tests"
    based_on: "docs/03_testing/contracts/TCS-*.md"
    tools: ["Pact", "Spring Cloud Contract"]
    gates:
      fail_when: "任何 Contract Test 失敗"

  integration_tests:
    description: "基於 Test Pyramid Spec 定義的整合層"
    based_on: "docs/03_testing/TEST-STRATEGY-{project}.md"
    target_ratio: "25-30% of total tests"  # 從策略文件取得
    gates:
      fail_when: "Integration Test 失敗率 > 0"

  e2e_tests:
    description: "覆蓋關鍵使用者旅程"
    based_on: "docs/03_testing/TEST-STRATEGY-{project}.md 中的使用者旅程清單"
    target_ratio: "10-15% of total tests"
    gates:
      fail_when: "關鍵使用者旅程測試失敗"

  rtm_coverage_report:
    description: "RTM 覆蓋率報告自動生成（SDD 新增）"
    output: "build/reports/RTM-Coverage-{date}.md"
    format:
      - "AC → AT 覆蓋率百分比"
      - "各 EPIC 測試覆蓋狀況"
      - "未覆蓋項目清單"
    gates:
      fail_when: "關鍵 AC（P0 功能）未覆蓋"
```

---

### 🔴 Quality Gate（品質閘門）

```yaml
quality_gate:
  description: "覆蓋率 < 目標時自動失敗（SDD 強制）"
  
  thresholds:
    unit_test_coverage: ">= 80%"       # 從 Test Strategy Spec 取得
    integration_coverage: ">= 70%"
    e2e_coverage_critical_paths: "100%" # 所有關鍵路徑必須覆蓋
    rtm_at_coverage: ">= 90%"
    
  fail_on_regression:
    enabled: true
    description: "覆蓋率相較上次 merge 降低 > 2% 時失敗"
    
  actions_on_failure:
    - "阻擋 PR Merge"
    - "建立 Quality Debt Issue（自動）"
    - "通知 QA Lead + 開發者"
```

---

### 🔔 Notify: Standard

```yaml
notifications:
  on_success:
    - channel: "Slack #qa-notifications"
      message: "✅ {branch} 測試通過 | Coverage: {coverage}% | RTM: {rtm_coverage}%"
      
  on_failure:
    - channel: "Slack #qa-alerts"
      message: "❌ {branch} 測試失敗 | Stage: {failed_stage} | 詳情: {report_url}"
    - email: "qa-lead@company.com"
```

---

## 📊 RTM Coverage Report 格式規格

```markdown
# RTM Coverage Report — {date}

## 摘要
| 指標 | 目標 | 實際 | 狀態 |
|------|------|------|------|
| Unit Test Coverage | ≥ 80% | {actual}% | ✅/❌ |
| AC → AT 覆蓋率 | ≥ 90% | {actual}% | ✅/❌ |
| 關鍵路徑 E2E 覆蓋 | 100% | {actual}% | ✅/❌ |

## 未覆蓋 AC 清單
| AC ID | Feature | 優先級 | 原因 |
|-------|---------|-------|------|

## Quality Gate 結果
□ 通過 / □ 失敗（原因：___）
```

---

## 🔗 相關文件

| 文件 | 路徑 |
|------|------|
| Test Strategy Spec 模板 | `docs_template/sdd/testing/TEST-STRATEGY-SPEC-TEMPLATE.md` |
| Test Contract Spec 模板 | `docs_template/sdd/testing/TEST-CONTRACT-SPEC-TEMPLATE.md` |
| RTM 模板 | `docs_template/sdd/testing/RTM-TEMPLATE.md` |
| Living Test Report 模板 | `docs_template/sdd/testing/LIVING-TEST-REPORT-TEMPLATE.md` |
| Defect Classification 模板 | `docs_template/sdd/testing/DEFECT-CLASSIFICATION-SPEC-TEMPLATE.md` |
| SDD CI/CD 基礎層 | `cicd/SDD_CICD_BASE_LAYER.md` |

---

> **SDD 原則**: 測試策略文件是 CI/CD 配置的上游輸入，Pipeline 規格必須與 Test Strategy Spec 保持一致。每次修改測試策略，必須同步評估 CI/CD 配置是否需要更新。
