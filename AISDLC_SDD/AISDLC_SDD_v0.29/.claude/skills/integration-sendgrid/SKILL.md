---
name: integration-sendgrid
description: SendGrid 郵件整合，ADR 記錄郵件服務選型，Email Template Spec 設計先行，RTM 追蹤
user-invocable: true
disable-model-invocation: false
argument-hint: "<email_type: transactional|marketing|both> [framework: nodejs|python|java]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# Integration SendGrid Skill（SDD 原生）

郵件整合在 SDD 中必須設計先行：郵件服務選型需有 ADR，Email Template Spec 定義所有郵件的觸發條件和內容規格，每種郵件類型需有對應的 TC 和 RTM 追蹤。

---

## 觸發方式

```bash
/integration-sendgrid transactional nodejs
/integration-sendgrid marketing
/integration-sendgrid both python
```

---

## 前置條件（SDD Spec-First）

| 閘門 | 說明 | 驗證方式 |
|------|------|---------|
| 🔷 SCG-1 通過 | 郵件架構確定 | SRD 通知架構章節 |
| FRD 郵件需求 | 郵件功能已定義為 F-XXX | 含 AC（發送 / 失敗 / 退訂）|

---

## 執行流程

### 階段 1：郵件服務選型 ADR

呼叫 `/adr-generate "郵件服務選型"`：

```markdown
# ADR-{NNN}: 郵件服務選型

## Decision
使用 SendGrid 作為郵件服務提供者

## Rationale
- 送達率高、提供詳細追蹤
- Template Engine 支援動態內容
- GDPR 合規：支援退訂管理（對應 NFR-COMP-XXX）

## Consequences
- Template 版本管理需在 SendGrid 平台處理
- Webhook 事件（bounce/spam）需有處理機制
```

---

### 階段 2：Email Template Spec

**文件路徑**：`docs/02_architecture/INTEGRATION-SPEC-Email-{System}.md`

```markdown
# Email Template Spec — {System}

## 郵件類型清單（對應 FRD Feature）

| 郵件 ID | 觸發事件 | FRD Feature | 收件人 | Template ID | 必要動態欄位 |
|---------|---------|------------|--------|------------|------------|
| EMAIL-001 | 用戶註冊 | F-USR-001 | 新用戶 | d-xxx001 | firstName, verificationUrl |
| EMAIL-002 | 密碼重設 | F-USR-003 | 請求用戶 | d-xxx002 | resetUrl（TTL: 1h）|
| EMAIL-003 | 訂單確認 | F-ORD-001 | 購買用戶 | d-xxx003 | orderNumber, items, totalAmount |

## 郵件規格（每封郵件）

### EMAIL-001: 用戶註冊確認
- **觸發**: POST /users 成功後
- **收件人**: req.body.email
- **主旨**: "確認您的 {SystemName} 帳號"
- **Template**: d-xxx001
- **動態欄位**:
  - `firstName`: string
  - `verificationUrl`: URL（TTL: 24h）
- **AC 對應**: AC-USR-001-3（用戶應在 5 分鐘內收到驗證信）
- **合規**: 含退訂連結（GDPR Art.21）
```

---

### 階段 3：API Contract 補充（郵件相關端點）

補充至 `CONTRACT-{Module}-v{N}.yaml`（若有郵件觸發 API）：

```yaml
/notifications/email:
  post:
    operationId: sendEmail
    summary: 觸發郵件發送
    x-sdd-feature-id: "F-NOTIFY-001"
    requestBody:
      content:
        application/json:
          schema:
            type: object
            required: [template_id, to, dynamic_data]
            properties:
              template_id: { type: string }
              to: { type: string, format: email }
              dynamic_data: { type: object }
    responses:
      '202': { description: 郵件已排入佇列 }
      '400': { $ref: '#/components/responses/BadRequest' }
```

---

### 階段 4：RTM 更新 🔴

```bash
/rtm-generate update
/spec-compliance-check docs/02_architecture/INTEGRATION-SPEC-Email-{System}.md
```

🔴 確認點：每個 Email Template 都有對應 TC（含 Sandbox 測試）；退訂機制符合 GDPR。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| 郵件服務選型 ADR | `docs/02_architecture/adr/ADR-{NNN}-email-service.md` | SCG-2 |
| Email Template Spec | `docs/02_architecture/INTEGRATION-SPEC-Email-{System}.md` | SCG-1 後 |

---

**基於**: AISDLC-SDD v0.29
**對應情境**: Integration 場景
