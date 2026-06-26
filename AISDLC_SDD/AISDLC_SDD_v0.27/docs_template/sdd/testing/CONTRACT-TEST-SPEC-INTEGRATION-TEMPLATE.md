# Contract Test Spec — Integration 整合契約測試規格模板
# 使用說明：複製至 docs/03_testing/contracts/CONTRACT-TEST-SPEC-{provider}.md 後填寫

**提供者**: {ProviderName}
**消費者**: {OurSystemName}
**版本**: v1.0
**建立日期**: {date}
**前置文件**: `CONSUMER-CONTRACT-{provider}.yaml`
**SCG 狀態**: 待 SCG-4 凍結
**spec-format-version**: 1.0  <!-- improving_85：AutoClaude SddToPlaybookAdapter 防漂移閘讀取（_SUPPORTED_SPEC_FORMAT_VERSIONS）；本契約格式跨版不相容演進時 bump 並同步 adapter 支援集 -->

---

## 1. 測試架構

```
Consumer Contract Tests（我們執行）
    ↓ 生成 Pact Contract
Provider Verification Tests（Provider 端執行，或 Mock 驗證）
    ↓ 驗證 Provider 符合 Contract
Contract Broker（Pact Broker / Git）
    ↓ 儲存並共享 Contract
CI/CD L2 自動執行
    ↓ 任何破壞性變更自動阻擋
```

---

## 2. Consumer Contract Test Cases

> 基於 `CONSUMER-CONTRACT-{provider}.yaml` 的每個 interaction

### TCS-CDC-001：{ProviderName} — 列表查詢成功路徑

```yaml
test_case: TCS-CDC-001
name: "GET {resources} 成功取得列表"
type: "Consumer Contract Test"
tool: "Pact（或相容框架）"

setup:
  mock_provider:
    interaction: "GET {resources} — 成功取得列表"  # 對應 CONSUMER-CONTRACT
    response_stub:
      status: 200
      body:
        data:
          - id: "test-uuid"
            {field}: "test-value"
        meta:
          total: 1

when:
  consumer_action: "呼叫 {OurSystem}.{ServiceName}.list{Resources}()"

then:
  - HTTP Request 格式符合 Contract
  - Response 正確解析為 Domain Model
  - ACL 翻譯邏輯正確（Provider Model → Domain Model）
  - 無 Exception 拋出

contract_verification:
  pact_file: "pacts/{OurSystem}-{ProviderName}.json"
  publish: true
```

### TCS-CDC-002：{ProviderName} — 建立資源成功路徑

```yaml
test_case: TCS-CDC-002
name: "POST {resources} 成功建立"
setup:
  mock_provider:
    interaction: "POST {resources} — 成功建立"
    response_stub:
      status: 201
      body:
        id: "new-uuid"
        status: "created"
when:
  consumer_action: "呼叫 {OurSystem}.{ServiceName}.create{Resource}({data})"
then:
  - 建立請求格式正確
  - 回應正確映射為 Domain Model
```

### TCS-CDC-003：{ProviderName} — 401 Token 過期處理

```yaml
test_case: TCS-CDC-003
name: "401 回應時自動刷新 Token 並重試"
setup:
  mock_provider:
    interaction: "GET {resources} — Token 無效時返回 401"
    response_stub:
      status: 401
      body: { error: "token_expired" }
when:
  consumer_action: "呼叫 list{Resources}()（使用過期 Token）"
then:
  - 系統自動觸發 Token 刷新
  - 刷新後重試原始請求
  - 最終返回正確結果（重試成功）
  - 不向上游暴露 401 錯誤
```

### TCS-CDC-004：{ProviderName} — 429 Rate Limit 處理

```yaml
test_case: TCS-CDC-004
name: "429 回應時指數退避重試"
setup:
  mock_provider:
    interaction: "GET {resources} — Rate Limit 超出時返回 429"
    response_stub:
      status: 429
      headers:
        Retry-After: "5"
when:
  consumer_action: "呼叫 list{Resources}()"
then:
  - 讀取 Retry-After Header
  - 等待指定時間後重試
  - 重試次數不超過 {N} 次
  - 超過重試次數後回傳 RateLimitError
```

### TCS-CDC-005：{ProviderName} — 500 伺服器錯誤降級

```yaml
test_case: TCS-CDC-005
name: "Provider 500 時返回 Fallback 回應"
setup:
  mock_provider: "持續回傳 500"
when:
  consumer_action: "呼叫 list{Resources}()"
then:
  - 熔斷器在 {N} 次後開啟
  - 返回 Fallback 回應（符合 CHAOS-CONTRACT）
  - 不拋出未處理的 Exception
```

---

## 3. Provider Verification Tests

> 驗證 Provider（第三方）的實際行為符合我們的 Consumer Contract

```yaml
provider_verification:
  provider: "{ProviderName}"
  consumer_contract_source: 
    type: "pact_broker"  # 或 "file"
    url: "{pact_broker_url}"
  
  verification_strategy: "mock"  # 使用 WireMock/Mock Server
  # 注意：若為第三方 Provider，通常使用 Mock 驗證而非真實呼叫
  
  test_environment: "staging"
  
  # 破壞性變更偵測
  breaking_change_detection:
    enabled: true
    fail_on: "any_contract_violation"
    notify: "{slack_channel}"
```

---

## 4. Contract Test 自動化 CI 整合

```yaml
# CI/CD L2 Contract Test 配置
contract_test_pipeline:
  trigger:
    - "任何 ACL 程式碼修改"
    - "任何 CONSUMER-CONTRACT-{provider}.yaml 修改"
    - "每日定時執行（偵測 Provider 變更）"
  
  steps:
    1_run_consumer_tests:
      command: "{contract test command}"
      publish_pacts: true
    
    2_verify_against_mock:
      command: "{provider verification command}"
    
    3_check_can_deploy:
      command: "pact-broker can-i-deploy --pacticipant {OurSystem} --to production"
  
  on_failure:
    - "Block PR merge"
    - "Notify: #integration-{provider} channel"
    - "Tag: 'CONTRACT_VIOLATION'"
```

---

## 5. 破壞性變更政策

| 變更類型 | 是否允許 | 處理方式 |
|---------|---------|---------|
| 新增可選回應欄位 | ✅ 允許 | 更新 Consumer Contract |
| 移除必填回應欄位 | ❌ 禁止 | 需版本升級 + 廢棄期 |
| 修改欄位型別 | ❌ 禁止 | 需版本升級 + 廢棄期 |
| 修改 HTTP Status Code | ❌ 禁止 | 需版本升級 |

---

## 6. SCG-4 凍結確認

- [ ] 所有 CONSUMER-CONTRACT interactions 均有對應 Test Case
- [ ] 成功路徑測試完整
- [ ] 錯誤路徑測試完整（401/429/500/Timeout）
- [ ] Provider Verification 測試已設定
- [ ] CI/CD L2 自動化整合已配置
- [ ] 破壞性變更偵測已啟用
- [ ] 🔴 Human 確認：測試規格凍結

**最後更新**: {date}
