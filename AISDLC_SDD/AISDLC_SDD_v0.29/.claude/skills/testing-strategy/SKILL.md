---
name: testing-strategy
description: 測試策略設計，Contract Testing 為新 L3，RTM 100% AC 覆蓋，測試金字塔對應 SCG-5
user-invocable: true
disable-model-invocation: false
argument-hint: "[framework: jest|vitest|pytest|junit] [scope: unit|integration|contract|e2e|full]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# Testing Strategy Skill（SDD 原生）

測試在 SDD 中是規格驅動的：測試策略不從「框架」出發，而從「RTM AC 覆蓋」出發。Contract Testing 是 SDD 測試金字塔的第三層（Consumer Contract + Provider Contract），必須在 SCG-3 後建立。測試完成後通過 RTM 100% 確認 SCG-5。

---

## 觸發方式

```bash
/testing-strategy full
/testing-strategy contract
/testing-strategy unit jest
```

---

## 前置條件（SDD Spec-First）

| 閘門 | 說明 | 驗證方式 |
|------|------|---------|
| 🔷 RTM 建立 | AC 已定義，TC 尚待建立 | `docs/03_testing/RTM-{System}.md` AC 列存在 |
| SCG-3 通過 | API Contract 凍結（Contract Testing 依據）| `CONTRACT-*.yaml` 存在 |

---

## 執行流程

### 階段 1：TEST-STRATEGY 文件產出

**文件路徑**：`docs/03_testing/TEST-STRATEGY-{SystemName}.md`

```markdown
# Test Strategy — {SystemName}

**對應 RTM**: `docs/03_testing/RTM-{SystemName}.md`
**對應 Contract**: `docs/02_architecture/api/CONTRACT-*.yaml`

## SDD 測試金字塔

```
        ┌─────────────┐
        │  E2E Tests  │  < 5%（Happy Path）
        │  Scenario   │  對應 AC 場景流程
        ├─────────────┤
        │  Contract   │  20%（SDD 核心）
        │  Testing    │  Consumer Contract + Provider Verify
        ├─────────────┤
        │ Integration │  25%
        │   Tests     │  Real DB / Real Queue
        ├─────────────┤
        │  Unit Tests │  50%（覆蓋率 ≥ 80%）
        │             │  Business Logic / Invariants
        └─────────────┘
```

## RTM 覆蓋策略

| AC 類型 | 測試層級 | TC 前綴 |
|---------|---------|---------|
| 業務邏輯 AC | Unit Test | TC-UNIT-XXX |
| API 互動 AC | Contract Test | TC-CONTRACT-XXX |
| 整合流程 AC | Integration Test | TC-INT-XXX |
| 端到端流程 AC | E2E Test | TC-E2E-XXX |
| 效能 NFR | Performance Test | TC-PERF-XXX |
| 安全 NFR | Security Test | TC-SEC-XXX |

## Contract Testing（SCG-3 後）

### Consumer Contract（Pact）
每個整合（OAuth / Stripe / AWS）都需要 Consumer Contract：

```javascript
// tests/contracts/user-service.pact.spec.ts
import { Pact } from '@pact-foundation/pact';

const provider = new Pact({
  consumer: '{SystemName}',
  provider: '{ExternalAPI}',
});

describe('User Service Contract', () => {
  it('should get user by id', async () => {
    await provider.addInteraction({
      state: 'user {id} exists',
      uponReceiving: 'a GET request for user {id}',
      withRequest: {
        method: 'GET',
        path: '/users/{id}',
        headers: { Authorization: 'Bearer valid_token' },
      },
      willRespondWith: {
        status: 200,
        body: {
          id: '{id}',
          email: like('user@example.com'),  // Contract 匹配
          name: like('John Doe'),
        },
      },
    });
    // 執行實際測試
  });
});
```

### Provider Contract Verification
Provider 端驗證 Consumer Contract 一致性：
```bash
# 在 CI/CD 的 contract-validation Stage 執行
pact-provider-verifier --provider-base-url http://localhost:3000 \
  --pact-broker-base-url {pact-broker-url}
```
```

---

### 階段 2：TC 撰寫規則（對應 RTM）

每個 TC 必須：
1. 有唯一 ID（TC-XXX-Y-Z 格式）
2. 明確對應 AC-XXX-Y
3. 有 Given / When / Then 結構
4. 屬於正確的測試層級

```typescript
// tests/unit/OrderService.spec.ts
// TC-UNIT-001-1: 對應 AC-ORD-001-1（訂單金額必須 > 0）
describe('OrderService.createOrder', () => {
  it('TC-UNIT-001-1: should throw when amount <= 0', () => {
    // Given: 訂單金額為 0
    const dto = { amount: 0, userId: 'user-1' };

    // When: 建立訂單
    // Then: 應拋出 INVALID_AMOUNT 錯誤
    expect(() => service.createOrder(dto)).toThrow('INVALID_AMOUNT');
    // → INV-003 Business Invariant 保護
  });
});
```

---

### 階段 3：RTM 更新 🔴

```bash
/rtm-generate update    # 填入 TC-XXX-Y-Z → 對應 AC-XXX-Y
/rtm-generate verify    # 確認覆蓋率 100%
/sdd-gate SCG-5         # RTM 100% → 提交交付閘門
```

🔴 確認點：RTM 無空白 TC（每個 AC 都有對應 TC）；Contract Testing 全部通過。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| Test Strategy | `docs/03_testing/TEST-STRATEGY-{System}.md` | SCG-3 後 |
| Consumer Contract | `docs/03_testing/contracts/CONSUMER-CONTRACT-*.md` | SCG-3 後 |

---

## 後置動作

```
/rtm-generate verify    # RTM 100% 確認
/sdd-gate SCG-5         # 測試通過，提交交付閘門
```

🔷 **本 Skill 協助通過**：SCG-5（RTM 100% 覆蓋）

---

## 相關 Skill

- `/rtm-generate` — RTM AC/TC 追蹤
- `/qa-testing` — QA 整合測試執行
- `/contract-generate` — OpenAPI Contract（Provider Contract 依據）

---

**基於**: AISDLC-SDD v0.29
**對應 CI/CD 規格**: `cicd/SDD_TESTING_CICD.md`
