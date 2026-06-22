---
name: integration-stripe
description: Stripe 支付整合，ADR 記錄支付策略，Webhook Contract 定義事件 Schema，RTM 追蹤支付 TC
user-invocable: true
disable-model-invocation: false
argument-hint: "<payment_type: one-time|subscription|both> [framework: nextjs|express|fastapi]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# Integration Stripe Skill（SDD 原生）

Stripe 整合在 SDD 中屬於「整合設計先行」範疇：支付策略需有 ADR，Webhook 事件需有 Event Schema Contract，支付 API 端點需在 OpenAPI Contract 中定義，每個支付 AC 需有對應 TC。

---

## 觸發方式

```bash
/integration-stripe one-time nextjs
/integration-stripe subscription express
/integration-stripe both
```

---

## 前置條件（SDD Spec-First）

| 閘門 | 說明 | 驗證方式 |
|------|------|---------|
| 🔷 SCG-1 通過 | 支付架構已決定 | `docs/02_architecture/SRD-{System}.md` 支付章節 |
| FRD 支付需求 | 支付功能已定義為 F-XXX | 含 AC（正常支付 / 失敗 / 退款 / 訂閱）|
| NFR-SEC-PCI 定義 | PCI-DSS 合規需求 | NFR-COMP-XXX 含 PCI 相關條款 |

---

## 執行流程

### 階段 1：支付策略 ADR（設計先行）🔴

呼叫 `/adr-generate "支付策略"`：

```markdown
# ADR-{NNN}: 支付策略與 Stripe 整合

## Decision
使用 Stripe Checkout（Hosted）+ Webhook 事件驅動 → 訂單狀態更新

## Rationale
- Hosted Checkout：PCI-DSS 合規範圍最小化（NFR-COMP-003）
- Webhook 非同步處理：確保支付結果可靠傳遞（冪等性）
- 不儲存 PAN：Token 化（對應 PCI-DSS Req.3）

## Payment Flow 設計
1. 前端觸發 → 後端建立 Checkout Session
2. 重導至 Stripe Hosted Page
3. 支付完成 → Stripe 發送 Webhook
4. 後端驗證 Webhook 簽章 → 更新訂單狀態

## Consequences
- Stripe Fee 結構需納入業務成本
- Webhook 必須冪等（重試安全）
- Refund 流程需單獨設計（F-XXX）
```

---

### 階段 2：Webhook Event Schema Contract

**文件路徑**：`docs/03_testing/contracts/WEBHOOK-CONTRACT-Stripe-{System}.md`

```markdown
# Webhook Contract — Stripe

**Provider**: Stripe API v{N}
**Consumer**: {SystemName}

## 訂閱事件清單（對應 FRD Feature）

| 事件類型 | 說明 | FRD Feature | 業務影響 |
|---------|------|------------|---------|
| payment_intent.succeeded | 支付成功 | F-PAY-001 | 訂單狀態 → 已付款 |
| payment_intent.payment_failed | 支付失敗 | F-PAY-002 | 通知用戶 + 訂單 → 待付款 |
| customer.subscription.created | 訂閱建立 | F-SUB-001 | 開通服務 |
| customer.subscription.deleted | 訂閱取消 | F-SUB-003 | 關閉服務 |
| charge.refunded | 退款 | F-PAY-005 | 訂單 → 已退款 |

## Webhook Payload 結構驗證（payment_intent.succeeded）
```json
{
  "id": "evt_xxx",                    // string, required
  "type": "payment_intent.succeeded", // string, required
  "data": {
    "object": {
      "id": "pi_xxx",                 // PaymentIntent ID, required
      "amount": 1000,                 // integer, cents, required
      "currency": "usd",              // string, required
      "metadata": {
        "order_id": "ORD-xxx"         // string, 必須含 order_id
      }
    }
  }
}
```

## 安全驗證
- Webhook 簽章驗證：`Stripe-Signature` header + Secret
- 冪等性：以 `event.id` 去重（防止重複處理）
```

---

### 階段 3：API Contract 補充（支付端點）

補充至 `docs/02_architecture/api/CONTRACT-{Module}-v{N}.yaml`：

```yaml
# 支付相關端點（對應 FRD F-PAY-XXX）
/payments/checkout:
  post:
    operationId: createCheckoutSession
    summary: 建立 Stripe Checkout Session
    x-sdd-feature-id: "F-PAY-001"
    requestBody:
      content:
        application/json:
          schema:
            type: object
            required: [order_id, amount, currency]
            properties:
              order_id: { type: string }
              amount: { type: integer, description: "金額（分）" }
              currency: { type: string, enum: [usd, twd] }
    responses:
      '200':
        content:
          application/json:
            schema:
              type: object
              properties:
                checkout_url: { type: string, format: uri }
      '400': { $ref: '#/components/responses/BadRequest' }
      '500': { $ref: '#/components/responses/InternalError' }

/payments/webhook:
  post:
    operationId: handleStripeWebhook
    summary: Stripe Webhook 接收端點
    x-sdd-feature-id: "F-PAY-001 F-PAY-002 F-PAY-005"
    description: |
      接收 Stripe Webhook 事件。
      必須驗證 `Stripe-Signature` header。
    responses:
      '200':
        description: 事件已接收並處理
      '400':
        description: 簽章驗證失敗
```

---

### 階段 4：RTM 更新 🔴

```bash
/rtm-generate update    # 更新支付相關 TC（TC-PAY-XXX）
/spec-compliance-check docs/03_testing/contracts/WEBHOOK-CONTRACT-Stripe-{System}.md
```

🔴 確認點：所有支付 AC（正常 / 失敗 / 退款）都有對應 TC，Consumer Contract 測試通過。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| 支付策略 ADR | `docs/02_architecture/adr/ADR-{NNN}-stripe-payment.md` | SCG-2 |
| Webhook Contract | `docs/03_testing/contracts/WEBHOOK-CONTRACT-Stripe-{System}.md` | SCG-3 後 |

---

## 後置動作

```
/rtm-generate update       # 更新支付 TC
/compliance-audit pci-dss  # PCI-DSS 合規確認
/sdd-gate SCG-4            # 支付整合 PR Review
```

🔷 **本 Skill 對應 SCG**：SCG-2（支付架構凍結）、SCG-4（整合 PR Review）

---

## 相關 Skill

- `/adr-generate` — 支付策略 ADR
- `/compliance-audit pci-dss` — PCI-DSS 合規（Stripe 整合必要）
- `/integration-webhook` — Webhook 通用設計
- `/security-audit` — 支付端點安全審查

---

**基於**: AISDLC-SDD v0.19
**對應情境**: Integration 場景
**CI/CD 規格**: `cicd/SDD_INTEGRATION_CICD.md`
