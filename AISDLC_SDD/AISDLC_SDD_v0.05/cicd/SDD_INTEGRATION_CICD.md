# Integration SDD CI/CD Pipeline 規格
# SDD Integration CI/CD Enhancement — Phase 04

**版本**: v1.0
**建立日期**: 2026-04-13
**適用情境**: Integration（第三方整合）
**前置條件**: `SDD_CICD_BASE_LAYER.md` 已定義

---

## Integration CI/CD 核心原則

> Consumer-Driven Contract 是 Integration CI/CD 的核心閘門

```
Integration Pipeline 特殊性：
  1. L0 新增 Consumer Contract 語法驗證
  2. L2 Consumer Contract Tests 為強制閘門（不可跳過）
  3. L2 Provider Contract Verification（驗證第三方符合期望）
  4. 任何破壞性 API 變更，CI 自動阻擋
  5. 整合失敗即時通知 Integration Owner
```

---

## Integration Pipeline 架構

```
L0: DocLint + Contract-Validate（Consumer Contract 語法驗證）
    ↓（通過）
L1: Unit Test + Mock Contract Test（單元層契約測試）
    ↓（通過）
SAST: 靜態安全掃描（包含認證安全掃描）
    ↓（通過）
Container: 容器化驗證
    ↓（通過）
L2 Contract Test（SDD 核心）:
    ├── Consumer Contract Tests 自動執行
    ├── Provider Contract Verification
    ├── Can-I-Deploy 檢查（Pact Broker）
    └── 任何破壞性變更自動阻擋
    ↓（全部通過）
L3 Deploy: Staging → Production（依 Canary）
    ↓
Notify: Advanced（整合失敗即時通知）
```

---

## L0 — 文件規格層（Integration 強化）

### Contract-Validate（🆕 Integration 專屬）

```yaml
contract_validate:
  name: "Consumer Contract 語法與完整性驗證"
  trigger: "docs/02_architecture/api/ 有 CONSUMER-CONTRACT-*.yaml 新增/修改"
  
  validation_rules:
    syntax:
      - "YAML 語法正確"
      - "Pact-Compatible 格式符合規範"
      - "所有 interactions 有 description"
    
    completeness:
      - "成功路徑 interaction 存在（2xx）"
      - "錯誤路徑 interaction 存在（401/429/500）"
      - "SLA expectations 已量化"
      - "error_handling_expectations 已定義"
    
    scg_gate:
      - "SCG 狀態為 Frozen 或 Review（非 Draft）"
      - "對應 THIRD-PARTY-API-RESEARCH-*.md 存在"
      - "對應 ADR-INTEGRATION-*.md 存在"
    
    cross_reference:
      - "每個 Consumer Contract interaction 有對應 Contract Test Case"
  
  tool: "python tools/consumer-contract-validator.py"
  fail_on_error: true
  output: "build/reports/verification/Contract-Validate-{date}.md"
```

---

## L1 — 建置測試層（Integration 強化）

### Mock Contract Test（L1 層快速驗證）

```yaml
mock_contract_test:
  name: "L1 Mock Consumer Contract Tests"
  description: "使用 Mock Server 執行輕量契約測試（L1 層，速度快）"
  trigger: "任何整合相關程式碼修改"
  
  tool: "WireMock / MockServer"
  environment: "本地 Docker Compose"
  
  scope:
    - "Happy path interactions（成功路徑）"
    - "認證流程驗證"
    - "ACL 翻譯邏輯驗證"
  
  execution_time_target: "< {N} 分鐘"
  
  note: "完整 Contract Tests 在 L2 執行（含 Pact Broker 驗證）"
```

---

## L2 — Contract Test Layer（SDD 核心，Integration 情境）

### Consumer Contract Tests

```yaml
consumer_contract_tests:
  name: "L2 Consumer Contract Tests"
  trigger: "PR to main / integration branches"
  type: "Consumer-Driven Contract Testing"
  
  tool: "Pact"
  
  execution:
    1_run_consumer_tests:
      command: "{consumer_test_command}"
      description: "執行所有 Consumer Contract Tests"
      scope: "所有 CONSUMER-CONTRACT-*.yaml 中的 interactions"
    
    2_publish_pacts:
      command: "pact-broker publish --consumer-app-version {version}"
      description: "發布 Pact 至 Broker"
    
    3_can_i_deploy:
      command: "pact-broker can-i-deploy --pacticipant {OurSystem} --to-environment production"
      description: "檢查是否可以安全部署（所有 Provider Contract 已驗證）"
  
  pass_criteria:
    - "所有 Consumer Contract interactions 測試通過"
    - "Pact Broker can-i-deploy 結果：YES"
  
  fail_behavior:
    - "Block PR merge"
    - "Notify: #integration-{provider}"
    - "Tag: 'CONSUMER_CONTRACT_FAIL'"
```

### Provider Contract Verification

```yaml
provider_contract_verification:
  name: "L2 Provider Contract Verification"
  trigger: "每日定時 + 任何 Provider API 變更通知"
  
  description: |
    驗證第三方 Provider 的實際行為（或 Mock）符合我們的 Consumer Contract。
    對於外部第三方：使用 Sandbox/Mock 環境
    對於內部 Provider：對接真實 Provider Verification
  
  execution:
    tool: "Pact Provider Verification"
    provider_base_url: "{provider_sandbox_url}"
    
    breaking_change_detection:
      enabled: true
      sources: "Pact Broker（所有 Consumer Contracts）"
      fail_on: "任何 Consumer Contract 違反"
      
    webhook_trigger:
      description: "Provider 程式碼變更時，自動觸發 Consumer 端驗證"
      endpoint: "{webhook_url}"
  
  fail_behavior:
    - "Block deployment"
    - "Notify: #integration-{provider} + @integration-owner"
    - "Tag: 'PROVIDER_CONTRACT_VIOLATION'"
    - "打開緊急 Issue"
```

### Contract Breaking Change 自動阻擋

```yaml
breaking_change_guard:
  name: "L2 Breaking Change Auto-Block"
  description: "任何可能破壞 Consumer Contract 的 API 變更自動被阻擋"
  
  protected_contracts:
    - "docs/02_architecture/api/CONSUMER-CONTRACT-*.yaml"
    - "docs/02_architecture/api/PROVIDER-API-SPEC-*.yaml"
  
  on_contract_modification:
    check_breaking_changes: true
    tool: "openapi-diff / Pact compatibility checks"
    fail_on: "breaking_change_detected"
    
  breaking_change_definition:
    - "移除必填回應欄位"
    - "修改欄位型別"
    - "修改 HTTP Status Code 語義"
    - "移除 API 端點（未廢棄直接刪除）"
    
  non_breaking_allowed:
    - "新增可選回應欄位"
    - "新增全新 API 端點"
    - "新增可選請求參數"
```

---

## 通知規格（Advanced — 整合失敗即時通知）

```yaml
integration_notifications:
  channels:
    integration: "#integration-{provider}"
    devops: "#devops-alerts"
  
  events:
    consumer_contract_fail:
      message: "🚨 Consumer Contract Test 失敗！\nProvider: {provider}\nInteraction: {interaction_desc}\n詳情: {run_url}"
      notify: ["integration-owner", "dev-lead"]
      priority: "URGENT"
      action: "Block PR + Open Issue"
    
    provider_contract_violation:
      message: "🚨 Provider Contract Violation！\n{ProviderName} 的回應不符合 Consumer Contract\n可能影響: {affected_interactions}\n詳情: {details_url}"
      notify: ["integration-owner", "tech-lead"]
      priority: "P0"
      action: "Block Deployment"
    
    can_i_deploy_no:
      message: "⛔ Can-I-Deploy 失敗\n原因: Consumer Contract 未驗證\n需要先完成 Provider Verification"
      notify: ["pr-author", "integration-owner"]
    
    daily_provider_check_fail:
      message: "📊 每日 Provider 驗證失敗\n{ProviderName} API 可能有破壞性變更\n請立即檢查"
      notify: ["integration-owner"]
      schedule: "每日 08:00"
    
    integration_healthy:
      message: "✅ 所有整合點 Contract Tests 通過\n{OurSystem} ↔ {ProviderName} 契約健康"
      notify: ["#integration-summary"]
```

---

## Integration Pipeline YAML 範例（GitHub Actions）

```yaml
name: Integration CI/CD Pipeline

on:
  push:
    branches: [main, feature/integration-*]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 0 * * *'  # 每日執行 Provider Verification

jobs:
  # L0: Consumer Contract 語法驗證
  contract_validate:
    name: "L0 Contract Validate"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate Consumer Contracts
        run: python tools/consumer-contract-validator.py

  # L1: Mock Contract Tests
  mock_contract_tests:
    name: "L1 Mock Contract Tests"
    needs: contract_validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Start Mock Servers
        run: docker-compose -f docker-compose.integration-test.yml up -d
      - name: Run Mock Contract Tests
        run: {mock_contract_test_command}

  # L2: Full Consumer Contract Tests
  consumer_contract_tests:
    name: "L2 Consumer Contract Tests"
    needs: mock_contract_tests
    runs-on: ubuntu-latest
    steps:
      - name: Run Consumer Contract Tests
        run: {consumer_contract_test_command}
      - name: Publish Pacts
        run: pact-broker publish --consumer-app-version ${{ github.sha }}
      - name: Can I Deploy
        run: |
          pact-broker can-i-deploy \
            --pacticipant {OurSystem} \
            --version ${{ github.sha }} \
            --to-environment production

  # L2: Provider Contract Verification (Daily or on Webhook)
  provider_verification:
    name: "L2 Provider Verification"
    if: github.event_name == 'schedule'
    runs-on: ubuntu-latest
    steps:
      - name: Verify Provider Contracts
        run: {provider_verification_command}
      - name: Notify on failure
        if: failure()
        run: {slack_notification_command}
```
