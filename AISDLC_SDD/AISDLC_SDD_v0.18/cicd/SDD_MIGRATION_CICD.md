# Migration SDD CI/CD Pipeline 規格
# SDD Migration CI/CD Enhancement — Phase 04

**版本**: v1.0
**建立日期**: 2026-04-13
**適用情境**: Migration（技術棧遷移）
**前置條件**: `SDD_CICD_BASE_LAYER.md` 已定義

---

## Migration CI/CD 核心原則

> Pipeline 即遷移的部署契約（MCM-Driven Pipeline）

```
Migration Pipeline 特殊性：
  1. L0 新增 MCM 完整性驗證（開發前必過）
  2. L2 所有 API 映射均需 Contract Test
  3. L3 嚴格按照 Canary Release Spec 執行
  4. 每遷移層完成後必須通知決策者
```

---

## Migration Pipeline 架構

```
L0: DocLint + MCM-Validate（MCM 完整性驗證）
    ↓（通過）
L1: Unit Test + Build Check
    ↓（通過）
SAST: 靜態安全掃描
    ↓（通過）
Container: 容器化驗證
    ↓（通過）
L2 Contract Test（SDD 強化）:
    ├── API Mapping Contract Tests（基於 MCM）
    ├── Data Integrity Tests
    └── Consumer-Driven Contract Tests
    ↓（全部通過）
🔴 Human Gate: 遷移層切換確認
    ↓（授權）
L3 Canary: 依 Canary Release Spec 執行
    ↓（全量通過）
Notify: Advanced（每層完成通知）
```

---

## L0 — 文件規格層（Migration 強化）

### MCM-Validate（🆕 Migration 專屬）

```yaml
mcm_validate:
  name: "Migration Contract Map 完整性驗證"
  trigger: "docs/02_architecture/migration/ 有新增或修改時"
  validation_rules:
    completeness:
      - "所有 API 映射均有 MCM-API-NNN 編號"
      - "每個 MCM-API 有明確的映射類型（1:1/合併/拆分/廢棄）"
      - "所有資料欄位映射均有 MCM-DATA-NNN 編號"
      - "Routing Contract 已定義流量分配計畫"
      - "Consistency Contract 已選擇一致性模型"
      - "Backward Compatibility Contract 廢棄期已定義"
    scg_gate:
      - "MCM 文件狀態為 Frozen（SCG-3 通過後）"
      - "Cutover Spec 存在"
      - "Rollback Spec 存在"
      - "Canary Spec 存在"
  fail_on_error: true
  output: "build/reports/verification/MCM-Validate-{date}.md"
```

---

## L2 — Migration Contract Test Layer（SDD 核心）

### API Mapping Contract Tests

```yaml
api_mapping_contract_tests:
  name: "L2 API Mapping Contract Tests"
  trigger: "PR to migration branch"
  requirements:
    - "每個 MCM-API 映射必須有對應 Contract Test"
    - "舊→新 API 回應等價性驗證"
    - "向後相容性：舊 API 在廢棄期內可用"
  
  test_spec: "docs/03_testing/contracts/CONTRACT-TEST-SPEC-{system}.md"
  
  execution:
    tool: "{Pact / Spring Cloud Contract / Postman Newman}"
    environment: "staging（雙系統並行環境）"
    parallel: true
  
  pass_criteria:
    - "所有 MCM-API 映射測試通過（100%）"
    - "向後相容性測試通過"
    - "無 API 回應格式不一致"
  
  fail_behavior:
    - "Block PR merge"
    - "Notify: #migration-{system}"
    - "標記: 'MCM_CONTRACT_VIOLATION'"
```

### Data Integrity Tests（自動化）

```yaml
data_integrity_tests:
  name: "L2 Data Integrity Tests"
  trigger: "每次資料遷移腳本修改 / 每層遷移前"
  
  tests:
    completeness:
      - query: "SELECT COUNT(*) 新舊系統比對"
      - tolerance: 0
    accuracy:
      - sampling_rate: "10%"
      - field_comparison: "按 MCM-DATA 規格"
    consistency:
      - foreign_key_check: true
      - business_rules: "見 DATA-INTEGRITY-TEST-SPEC"
  
  pass_criteria: "差異 = 0 筆，抽樣 100% 通過"
  fail_behavior: "Fail Build + 立即通知 DBA"
```

### Consumer-Driven Contract Tests

```yaml
consumer_driven_contract:
  name: "L2 Consumer-Driven Contract Tests"
  trigger: "任何 API/Service 程式碼修改"
  tool: "Pact"
  
  consumer_tests:
    - 舊系統作為消費者，驗證新系統 API 符合期望
    - 新系統作為消費者，驗證 API 客戶端行為
  
  provider_verification:
    - 新系統 API 驗證符合所有 Consumer Contracts
  
  breaking_change_detection:
    enabled: true
    fail_on: "any_violation"
```

---

## L3 — Canary 部署層（依 Canary Spec）

```yaml
canary_deployment:
  name: "L3 Migration Canary Deploy"
  trigger: "Human Gate 通過 + L2 全部通過"
  
  canary_spec: "docs/08_deployment/CANARY-SPEC-{system}.md"
  
  phases:
    phase_1:
      traffic: "5%"
      duration: "{N}h"
      auto_proceed: false  # 必須 Human 確認
      monitoring:
        error_rate_threshold: "{%}"
        latency_p95_threshold: "{N}ms"
    
    phase_2:
      traffic: "25%"
      duration: "{N}h"
      auto_proceed: false
    
    phase_final:
      traffic: "100%"
      requires: "🔴 Human 最終授權"
  
  auto_rollback:
    enabled: true
    trigger: "錯誤率 > {%} 持續 {N}min"
    spec: "docs/08_deployment/ROLLBACK-SPEC-{system}.md"
```

---

## 通知規格（Advanced）

```yaml
migration_notifications:
  channels:
    primary: "#migration-{system}"
    devops: "#devops-alerts"
    stakeholders: "#release-{system}"
  
  events:
    layer_complete:
      message: "✅ 遷移層 {layer} 完成 — {system}\n切換率: {%}%\n下一步: 🔴 Human 確認 Phase {N+1}"
      notify: ["tech-lead", "pm", "decision-maker"]
    
    contract_violation:
      message: "🚨 Contract Violation!\nAPI Mapping: {MCM-ID}\n詳情: {URL}"
      notify: ["migration-team", "dev-lead"]
      priority: "URGENT"
    
    data_integrity_fail:
      message: "🚨 Data Integrity Failure!\n差異: {N} 筆\n立即停止遷移"
      notify: ["dba", "tech-lead", "decision-maker"]
      priority: "P0"
    
    canary_phase_complete:
      message: "📊 Canary Phase {N} 完成 ({%}%)\n錯誤率: {%}\nP95: {N}ms\n授權下一階段？"
      notify: ["decision-maker"]
      action_required: true
    
    rollback_triggered:
      message: "⚠️ 回滾觸發！原因: {reason}\n正在執行 Rollback Spec..."
      notify: ["all-hands"]
      priority: "P0"
    
    migration_complete:
      message: "🎉 {system} 遷移完成！100% 流量已切換至新系統"
      notify: ["all-stakeholders"]
```

---

## Migration Pipeline YAML 範例（GitHub Actions）

```yaml
name: Migration CI/CD Pipeline

on:
  push:
    branches: [migration/*, main]
  pull_request:
    branches: [migration/*]

jobs:
  # L0: MCM 驗證
  mcm_validate:
    name: "L0 MCM Validate"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate MCM completeness
        run: python tools/mcm-validator.py docs/02_architecture/migration/

  # L1: Build + Unit Test
  build_test:
    name: "L1 Build & Test"
    needs: mcm_validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build
        run: {build_command}
      - name: Unit Tests
        run: {test_command}

  # L2: Contract Tests
  contract_tests:
    name: "L2 Contract Tests"
    needs: build_test
    runs-on: ubuntu-latest
    steps:
      - name: Start test environment
        run: docker-compose -f docker-compose.migration-test.yml up -d
      - name: API Mapping Contract Tests
        run: {contract_test_command}
      - name: Data Integrity Tests
        run: {data_integrity_test_command}
      - name: Consumer-Driven Contract Tests
        run: {cdc_test_command}

  # L3: Human Gate + Canary
  canary_gate:
    name: "L3 Canary Deploy (Requires Human Approval)"
    needs: contract_tests
    environment: migration-production  # GitHub Environment with required reviewers
    runs-on: ubuntu-latest
    steps:
      - name: Deploy Canary Phase 1 (5%)
        run: {canary_phase1_command}
      - name: Monitor Phase 1
        run: {monitoring_check_command}
```
