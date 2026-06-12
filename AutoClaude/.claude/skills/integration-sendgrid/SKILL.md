---
name: integration-sendgrid
description: 整合 SendGrid 郵件服務，包含模板郵件、批量發送、追蹤
user-invocable: true
disable-model-invocation: false
argument-hint: "[feature: 功能 (transactional/marketing/templates)]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
  - Bash
---

# Integration SendGrid Skill

整合 SendGrid 郵件發送服務。

---

## 觸發方式

```bash
/integration-sendgrid                # 基本整合
/integration-sendgrid templates      # 模板郵件
/integration-sendgrid marketing      # 行銷郵件
```

---

## 執行流程

### 階段 1: SendGrid 設定 🔴

**確認項目**:
- [ ] SendGrid 帳戶已建立
- [ ] API Key 已取得
- [ ] 寄件者驗證完成
- [ ] 郵件模板已建立 (可選)

**環境變數**:
```env
SENDGRID_API_KEY=SG...
SENDGRID_FROM_EMAIL=noreply@example.com
SENDGRID_FROM_NAME=My App
```

🔴 **確認點**: 確認 SendGrid 配置

---

### 階段 2: 基礎郵件服務

```typescript
// src/lib/email/sendgrid.ts
import sgMail from '@sendgrid/mail';

sgMail.setApiKey(process.env.SENDGRID_API_KEY!);

interface EmailParams {
  to: string | string[];
  subject: string;
  html: string;
  text?: string;
  from?: {
    email: string;
    name?: string;
  };
  replyTo?: string;
  attachments?: Array<{
    content: string;
    filename: string;
    type?: string;
    disposition?: 'attachment' | 'inline';
  }>;
}

interface TemplateEmailParams {
  to: string | string[];
  templateId: string;
  dynamicTemplateData: Record<string, unknown>;
  from?: {
    email: string;
    name?: string;
  };
}

export const emailService = {
  // 發送基本郵件
  async send(params: EmailParams) {
    const msg = {
      to: params.to,
      from: params.from || {
        email: process.env.SENDGRID_FROM_EMAIL!,
        name: process.env.SENDGRID_FROM_NAME,
      },
      subject: params.subject,
      html: params.html,
      text: params.text,
      replyTo: params.replyTo,
      attachments: params.attachments,
    };

    await sgMail.send(msg);
  },

  // 使用模板發送
  async sendTemplate(params: TemplateEmailParams) {
    const msg = {
      to: params.to,
      from: params.from || {
        email: process.env.SENDGRID_FROM_EMAIL!,
        name: process.env.SENDGRID_FROM_NAME,
      },
      templateId: params.templateId,
      dynamicTemplateData: params.dynamicTemplateData,
    };

    await sgMail.send(msg);
  },

  // 批量發送
  async sendBatch(messages: EmailParams[]) {
    const msgs = messages.map((params) => ({
      to: params.to,
      from: params.from || {
        email: process.env.SENDGRID_FROM_EMAIL!,
        name: process.env.SENDGRID_FROM_NAME,
      },
      subject: params.subject,
      html: params.html,
      text: params.text,
    }));

    await sgMail.send(msgs);
  },
};
```

---

### 階段 3: 郵件模板系統

```typescript
// src/lib/email/templates.ts
export const emailTemplates = {
  // 歡迎郵件
  welcome: (name: string) => ({
    subject: `歡迎加入，${name}！`,
    html: `
      <!DOCTYPE html>
      <html>
        <head>
          <style>
            .container { max-width: 600px; margin: 0 auto; font-family: sans-serif; }
            .header { background: #4F46E5; color: white; padding: 20px; text-align: center; }
            .content { padding: 30px; }
            .button { background: #4F46E5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; }
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <h1>歡迎加入！</h1>
            </div>
            <div class="content">
              <p>親愛的 ${name}，</p>
              <p>感謝您註冊我們的服務！我們很高興您的加入。</p>
              <p style="text-align: center; margin: 30px 0;">
                <a href="${process.env.NEXT_PUBLIC_URL}/dashboard" class="button">
                  開始使用
                </a>
              </p>
            </div>
          </div>
        </body>
      </html>
    `,
  }),

  // 密碼重設
  passwordReset: (name: string, resetUrl: string) => ({
    subject: '重設您的密碼',
    html: `
      <!DOCTYPE html>
      <html>
        <head>
          <style>
            .container { max-width: 600px; margin: 0 auto; font-family: sans-serif; }
            .content { padding: 30px; }
            .button { background: #4F46E5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; }
            .warning { color: #6B7280; font-size: 12px; }
          </style>
        </head>
        <body>
          <div class="container">
            <div class="content">
              <p>親愛的 ${name}，</p>
              <p>我們收到了您的密碼重設請求。請點擊下方按鈕重設密碼：</p>
              <p style="text-align: center; margin: 30px 0;">
                <a href="${resetUrl}" class="button">重設密碼</a>
              </p>
              <p class="warning">
                此連結將在 1 小時後失效。如果您沒有請求重設密碼，請忽略此郵件。
              </p>
            </div>
          </div>
        </body>
      </html>
    `,
  }),

  // 訂單確認
  orderConfirmation: (order: {
    orderNumber: string;
    customerName: string;
    items: Array<{ name: string; quantity: number; price: number }>;
    total: number;
  }) => ({
    subject: `訂單確認 #${order.orderNumber}`,
    html: `
      <!DOCTYPE html>
      <html>
        <head>
          <style>
            .container { max-width: 600px; margin: 0 auto; font-family: sans-serif; }
            .header { background: #10B981; color: white; padding: 20px; text-align: center; }
            .content { padding: 30px; }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 10px; text-align: left; border-bottom: 1px solid #E5E7EB; }
            .total { font-weight: bold; font-size: 18px; }
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <h1>訂單確認</h1>
              <p>訂單編號: ${order.orderNumber}</p>
            </div>
            <div class="content">
              <p>親愛的 ${order.customerName}，</p>
              <p>感謝您的訂購！以下是您的訂單明細：</p>
              <table>
                <tr>
                  <th>商品</th>
                  <th>數量</th>
                  <th>金額</th>
                </tr>
                ${order.items
                  .map(
                    (item) => `
                  <tr>
                    <td>${item.name}</td>
                    <td>${item.quantity}</td>
                    <td>$${item.price}</td>
                  </tr>
                `
                  )
                  .join('')}
                <tr>
                  <td colspan="2" class="total">總計</td>
                  <td class="total">$${order.total}</td>
                </tr>
              </table>
            </div>
          </div>
        </body>
      </html>
    `,
  }),
};
```

---

### 階段 4: 郵件服務整合

```typescript
// src/services/notification.ts
import { emailService } from '@/lib/email/sendgrid';
import { emailTemplates } from '@/lib/email/templates';

export const notificationService = {
  async sendWelcomeEmail(email: string, name: string) {
    const template = emailTemplates.welcome(name);
    await emailService.send({
      to: email,
      subject: template.subject,
      html: template.html,
    });
  },

  async sendPasswordResetEmail(email: string, name: string, token: string) {
    const resetUrl = `${process.env.NEXT_PUBLIC_URL}/reset-password?token=${token}`;
    const template = emailTemplates.passwordReset(name, resetUrl);
    await emailService.send({
      to: email,
      subject: template.subject,
      html: template.html,
    });
  },

  async sendOrderConfirmation(email: string, order: Parameters<typeof emailTemplates.orderConfirmation>[0]) {
    const template = emailTemplates.orderConfirmation(order);
    await emailService.send({
      to: email,
      subject: template.subject,
      html: template.html,
    });
  },
};
```

---

### 階段 5: 驗證 🔴

**驗證清單**:
- [ ] 基本郵件發送成功
- [ ] 模板郵件正確渲染
- [ ] 批量發送正常
- [ ] 錯誤處理正確
- [ ] 郵件到達率正常

🔴 **確認點**: 確認郵件服務運作正常

---

## 產出物

| 產出物 | 路徑 |
|--------|------|
| SendGrid 服務 | `src/lib/email/sendgrid.ts` |
| 郵件模板 | `src/lib/email/templates.ts` |
| 通知服務 | `src/services/notification.ts` |

---

## 相關 Skill

- `/integration-aws` - AWS SES 替代方案
- `/integration-webhook` - 郵件事件處理

---


## 相關檔案

- SOP 參考: `scenarios/integration/SOP_QuickRef.md`

**基於**: AISDLC v0.09 Integration 情境
