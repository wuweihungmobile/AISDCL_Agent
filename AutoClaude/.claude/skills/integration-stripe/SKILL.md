---
name: integration-stripe
description: 整合 Stripe 支付系統，包含結帳流程、Webhook 處理、訂閱管理
user-invocable: true
disable-model-invocation: false
argument-hint: "<payment_type: 支付類型 (one-time/subscription/both)> [framework: 使用的框架 (nextjs/express/fastapi)]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
  - Bash
---

# Integration Stripe Payment Skill

基於 AISDLC Integration 情境的 Stripe 支付整合技能。

---

## 觸發方式

```bash
/integration-stripe one-time nextjs
/integration-stripe subscription express
/integration-stripe --payment_type=both
```

---

## 執行流程

### 階段 1: Stripe 設定確認 🔴

**必要資訊**:
- [ ] Stripe 帳戶已建立
- [ ] API Keys 已取得 (Publishable + Secret)
- [ ] Webhook Endpoint 已規劃
- [ ] 產品/價格已在 Stripe Dashboard 建立

**環境變數**:
```env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

🔴 **確認點**: 確認 API Keys 和產品設定

---

### 階段 2: 後端整合

#### 安裝依賴

```bash
npm install stripe
```

#### Stripe 客戶端初始化

```typescript
// lib/stripe.ts
import Stripe from 'stripe';

export const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2023-10-16',
  typescript: true,
});
```

#### 建立 Checkout Session (一次性支付)

```typescript
// app/api/checkout/route.ts (Next.js)
import { stripe } from '@/lib/stripe';
import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  const { priceId, quantity = 1 } = await req.json();

  try {
    const session = await stripe.checkout.sessions.create({
      mode: 'payment',
      payment_method_types: ['card'],
      line_items: [
        {
          price: priceId,
          quantity,
        },
      ],
      success_url: `${process.env.NEXT_PUBLIC_URL}/success?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${process.env.NEXT_PUBLIC_URL}/cancel`,
      metadata: {
        // 自訂資料
      },
    });

    return NextResponse.json({ sessionId: session.id, url: session.url });
  } catch (error) {
    return NextResponse.json({ error: 'Checkout failed' }, { status: 500 });
  }
}
```

#### 建立訂閱 Checkout

```typescript
// app/api/subscribe/route.ts
export async function POST(req: Request) {
  const { priceId, customerId } = await req.json();

  const session = await stripe.checkout.sessions.create({
    mode: 'subscription',
    customer: customerId,
    line_items: [{ price: priceId, quantity: 1 }],
    success_url: `${process.env.NEXT_PUBLIC_URL}/subscription/success`,
    cancel_url: `${process.env.NEXT_PUBLIC_URL}/pricing`,
  });

  return NextResponse.json({ url: session.url });
}
```

---

### 階段 3: Webhook 處理

```typescript
// app/api/webhook/route.ts
import { stripe } from '@/lib/stripe';
import { headers } from 'next/headers';

export async function POST(req: Request) {
  const body = await req.text();
  const signature = headers().get('stripe-signature')!;

  let event: Stripe.Event;

  try {
    event = stripe.webhooks.constructEvent(
      body,
      signature,
      process.env.STRIPE_WEBHOOK_SECRET!
    );
  } catch (err) {
    return new Response('Webhook signature verification failed', { status: 400 });
  }

  switch (event.type) {
    case 'checkout.session.completed':
      const session = event.data.object as Stripe.Checkout.Session;
      // 處理成功付款
      await handleSuccessfulPayment(session);
      break;

    case 'invoice.paid':
      const invoice = event.data.object as Stripe.Invoice;
      // 處理訂閱續費
      await handleSubscriptionRenewal(invoice);
      break;

    case 'customer.subscription.deleted':
      const subscription = event.data.object as Stripe.Subscription;
      // 處理訂閱取消
      await handleSubscriptionCancellation(subscription);
      break;

    default:
      console.log(`Unhandled event type: ${event.type}`);
  }

  return new Response('OK', { status: 200 });
}

async function handleSuccessfulPayment(session: Stripe.Checkout.Session) {
  // 1. 更新資料庫訂單狀態
  // 2. 發送確認郵件
  // 3. 開通服務權限
}
```

---

### 階段 4: 前端整合

#### 安裝 Stripe.js

```bash
npm install @stripe/stripe-js @stripe/react-stripe-js
```

#### Stripe Provider

```typescript
// components/StripeProvider.tsx
'use client';

import { Elements } from '@stripe/react-stripe-js';
import { loadStripe } from '@stripe/stripe-js';

const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!);

export function StripeProvider({ children }: { children: React.ReactNode }) {
  return <Elements stripe={stripePromise}>{children}</Elements>;
}
```

#### 結帳按鈕

```typescript
// components/CheckoutButton.tsx
'use client';

export function CheckoutButton({ priceId }: { priceId: string }) {
  const [loading, setLoading] = useState(false);

  const handleCheckout = async () => {
    setLoading(true);
    const res = await fetch('/api/checkout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ priceId }),
    });
    const { url } = await res.json();
    window.location.href = url;
  };

  return (
    <button onClick={handleCheckout} disabled={loading}>
      {loading ? '處理中...' : '立即購買'}
    </button>
  );
}
```

---

### 階段 5: 測試驗證

**測試卡號**:
| 卡號 | 情境 |
|------|------|
| 4242 4242 4242 4242 | 成功支付 |
| 4000 0000 0000 9995 | 餘額不足 |
| 4000 0000 0000 0341 | 卡片被拒 |

**Webhook 測試**:
```bash
# 安裝 Stripe CLI
stripe listen --forward-to localhost:3000/api/webhook

# 觸發測試事件
stripe trigger checkout.session.completed
```

**驗證清單**:
- [ ] Checkout 流程正常
- [ ] 付款成功後正確跳轉
- [ ] Webhook 正確接收和處理
- [ ] 訂閱狀態正確更新
- [ ] 錯誤情況正確處理

---

## 常見陷阱

| 問題 | 解決方案 |
|------|---------|
| Webhook 驗證失敗 | 確認使用 raw body，非 JSON parsed |
| 重複處理 | 使用 idempotency key |
| 價格不匹配 | 使用 Price ID 而非硬編碼金額 |

---

## 產出物

| 產出物 | 路徑 |
|--------|------|
| Stripe 客戶端 | `lib/stripe.ts` |
| Checkout API | `app/api/checkout/route.ts` |
| Webhook 處理 | `app/api/webhook/route.ts` |
| 前端元件 | `components/CheckoutButton.tsx` |

---

## 相關 Skill

- `/integration-oauth` - 用戶認證
- `/security` - 支付安全審查

---


## 相關檔案

- SOP 參考: `scenarios/integration/SOP_QuickRef.md`

**基於**: AISDLC v0.09 Integration 情境
