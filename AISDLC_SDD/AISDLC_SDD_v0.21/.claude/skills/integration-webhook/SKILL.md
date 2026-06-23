---
name: integration-webhook
description: Webhook 系統設計，Event Schema Contract 先行，簽章驗證 ADR，冪等性規格，RTM 追蹤
user-invocable: true
disable-model-invocation: false
argument-hint: "<direction: receive|send|both> [provider: stripe|github|custom]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# Integration Webhook Skill（SDD 原生）

Webhook 在 SDD 中必須設計先行：Event Schema Contract 定義事件格式，ADR 記錄安全驗證策略，冪等性設計在實作前凍結。本 Skill 適用於接收外部 Webhook（如 Stripe）和發送 Webhook 給下游消費者。

---

## 觸發方式

```bash
/integration-webhook receive stripe
/integration-webhook send custom
/integration-webhook both
```

---

## 前置條件（SDD Spec-First）

| 閘門 | 說明 | 驗證方式 |
|------|------|---------|
| 🔷 SCG-1 通過 | Webhook 架構確定 | `docs/02_architecture/SRD-{System}.md` 事件架構章節 |
| FRD 事件需求 | Webhook 事件已定義為 F-XXX | 含 AC（事件接收 / 失敗重試 / 冪等）|

---

## 執行流程

### 階段 1：Webhook 安全策略 ADR

呼叫 `/adr-generate "Webhook 安全與冪等策略"`：

```markdown
# ADR-{NNN}: Webhook 安全驗證與冪等性設計

## Decision
使用 HMAC-SHA256 簽章驗證 + event_id 去重（Redis）

## Rationale
- HMAC 驗證：防止偽造 Webhook（STRIDE T-001）
- event_id 去重：確保冪等性（Webhook 可能重複發送）
- 非同步處理：接收立即返回 200，處理邏輯進佇列

## Consequences
- 需要儲存已處理的 event_id（TTL = 24h）
- 重試邏輯：3 次，指數退避
```

---

### 階段 2：Event Schema Contract

**文件路徑**：`docs/03_testing/contracts/WEBHOOK-CONTRACT-{Provider}-{System}.md`

```markdown
# Webhook Event Schema Contract — {Provider}

**方向**: Receive（接收）/ Send（發送）
**版本**: 與 API Contract 同步

## 訂閱事件清單（對應 FRD Feature）

| 事件類型 | 說明 | FRD Feature | 業務影響 |
|---------|------|------------|---------|
| {event.type} | {說明} | F-XXX | {業務影響} |

## 事件 Payload Schema

```json
{
  "event_id": "string（唯一 ID，用於冪等去重）",
  "event_type": "string（事件類型）",
  "timestamp": "string（ISO 8601）",
  "data": {
    // 事件特定資料
  },
  "signature": "string（HMAC-SHA256，用於驗證）"
}
```

## 安全驗證規格
- Header: `X-Webhook-Signature: sha256={HMAC}`
- Secret: 環境變數 `WEBHOOK_SECRET`（不可 hardcode）
- 驗證失敗返回：400

## 冪等性規格
- 去重 Key: `event_id`
- 去重儲存: Redis SET（TTL = 24h）
- 重複事件：返回 200（不重複處理）
```

---

### 階段 3：Webhook 端點 Contract 補充

補充至 `docs/02_architecture/api/CONTRACT-{Module}-v{N}.yaml`：

```yaml
/webhooks/{provider}:
  post:
    operationId: receive{Provider}Webhook
    summary: 接收 {Provider} Webhook 事件
    x-sdd-feature-id: "F-WEBHOOK-001"
    parameters:
      - name: X-Webhook-Signature
        in: header
        required: true
        schema: { type: string }
    responses:
      '200':
        description: 事件已接收（非同步處理）
      '400':
        description: 簽章驗證失敗
```

---

### 階段 4：RTM 更新 🔴

```bash
/rtm-generate update
/spec-compliance-check docs/03_testing/contracts/WEBHOOK-CONTRACT-{Provider}-{System}.md
```

🔴 確認點：冪等性 TC（TC-WH-002）已建立；簽章驗證 TC（TC-WH-001）已建立。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| Webhook 安全 ADR | `docs/02_architecture/adr/ADR-{NNN}-webhook-security.md` | SCG-2 |
| Event Schema Contract | `docs/03_testing/contracts/WEBHOOK-CONTRACT-{Provider}-{System}.md` | SCG-3 後 |

---

**基於**: AISDLC-SDD v0.21
**CI/CD 規格**: `cicd/SDD_INTEGRATION_CICD.md`
