---
name: integration-webhook
description: 建立 Webhook 處理系統，包含驗證、重試、事件處理
user-invocable: true
disable-model-invocation: false
argument-hint: "[provider: Webhook 來源 (stripe/github/custom)] [framework: 框架 (nextjs/express/fastapi/spring)]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
  - Bash
---

# Integration Webhook Skill

建立企業級 Webhook 處理系統。

---

## 觸發方式

```bash
/integration-webhook                  # 通用 Webhook
/integration-webhook stripe nextjs    # Stripe + Next.js
/integration-webhook github express   # GitHub + Express
```

---

## 執行流程

### 階段 1: 需求確認 🔴

**確認項目**:
- [ ] Webhook 來源和事件類型
- [ ] 驗證機制 (簽名/Secret)
- [ ] 重試和冪等性策略
- [ ] 事件處理邏輯
- [ ] 錯誤處理和告警

🔴 **確認點**: 確認 Webhook 需求

---

### 階段 2: Webhook 處理架構

```typescript
// src/lib/webhook/types.ts
export interface WebhookEvent<T = unknown> {
  id: string;
  type: string;
  timestamp: number;
  data: T;
  signature?: string;
}

export interface WebhookHandler<T = unknown> {
  eventType: string;
  handle: (event: WebhookEvent<T>) => Promise<void>;
}

export interface WebhookConfig {
  secret: string;
  toleranceSeconds?: number;
}
```

```typescript
// src/lib/webhook/processor.ts
import crypto from 'crypto';
import { WebhookEvent, WebhookHandler, WebhookConfig } from './types';

export class WebhookProcessor {
  private handlers = new Map<string, WebhookHandler>();
  private config: WebhookConfig;

  constructor(config: WebhookConfig) {
    this.config = config;
  }

  register<T>(handler: WebhookHandler<T>): void {
    this.handlers.set(handler.eventType, handler as WebhookHandler);
  }

  verifySignature(payload: string, signature: string): boolean {
    const expectedSignature = crypto
      .createHmac('sha256', this.config.secret)
      .update(payload)
      .digest('hex');

    return crypto.timingSafeEqual(
      Buffer.from(signature),
      Buffer.from(`sha256=${expectedSignature}`)
    );
  }

  async process(event: WebhookEvent): Promise<void> {
    const handler = this.handlers.get(event.type);

    if (!handler) {
      console.warn(`No handler for event type: ${event.type}`);
      return;
    }

    await handler.handle(event);
  }
}
```

---

### 階段 3: Next.js Webhook Endpoint

```typescript
// app/api/webhook/route.ts
import { headers } from 'next/headers';
import { NextResponse } from 'next/server';
import { WebhookProcessor } from '@/lib/webhook/processor';
import { handleOrderCreated, handlePaymentCompleted } from '@/lib/webhook/handlers';

const processor = new WebhookProcessor({
  secret: process.env.WEBHOOK_SECRET!,
});

// 註冊處理器
processor.register(handleOrderCreated);
processor.register(handlePaymentCompleted);

export async function POST(req: Request) {
  const body = await req.text();
  const headersList = headers();
  const signature = headersList.get('x-webhook-signature');

  // 驗證簽名
  if (!signature || !processor.verifySignature(body, signature)) {
    return NextResponse.json(
      { error: 'Invalid signature' },
      { status: 401 }
    );
  }

  try {
    const event = JSON.parse(body);

    // 冪等性檢查
    const processed = await checkIdempotency(event.id);
    if (processed) {
      return NextResponse.json({ status: 'already_processed' });
    }

    // 處理事件
    await processor.process(event);

    // 標記為已處理
    await markAsProcessed(event.id);

    return NextResponse.json({ status: 'success' });
  } catch (error) {
    console.error('Webhook processing error:', error);
    return NextResponse.json(
      { error: 'Processing failed' },
      { status: 500 }
    );
  }
}

// 冪等性函數
async function checkIdempotency(eventId: string): Promise<boolean> {
  // 使用 Redis 或資料庫檢查
  // return await redis.exists(`webhook:${eventId}`);
  return false;
}

async function markAsProcessed(eventId: string): Promise<void> {
  // await redis.set(`webhook:${eventId}`, '1', 'EX', 86400 * 7);
}
```

---

### 階段 4: 事件處理器

```typescript
// src/lib/webhook/handlers/order.ts
import { WebhookHandler, WebhookEvent } from '../types';
import { prisma } from '@/lib/prisma';

interface OrderData {
  orderId: string;
  customerId: string;
  items: Array<{ productId: string; quantity: number }>;
  total: number;
}

export const handleOrderCreated: WebhookHandler<OrderData> = {
  eventType: 'order.created',

  async handle(event: WebhookEvent<OrderData>) {
    const { orderId, customerId, items, total } = event.data;

    // 1. 儲存訂單
    await prisma.order.create({
      data: {
        externalId: orderId,
        customerId,
        total,
        items: {
          create: items.map((item) => ({
            productId: item.productId,
            quantity: item.quantity,
          })),
        },
        webhookEventId: event.id,
      },
    });

    // 2. 發送通知
    await sendOrderConfirmation(customerId, orderId);

    // 3. 更新庫存
    for (const item of items) {
      await updateInventory(item.productId, -item.quantity);
    }

    console.log(`Order ${orderId} processed successfully`);
  },
};

export const handlePaymentCompleted: WebhookHandler<{ orderId: string; amount: number }> = {
  eventType: 'payment.completed',

  async handle(event) {
    const { orderId, amount } = event.data;

    await prisma.order.update({
      where: { externalId: orderId },
      data: {
        paymentStatus: 'COMPLETED',
        paidAmount: amount,
        paidAt: new Date(),
      },
    });

    console.log(`Payment for order ${orderId} completed`);
  },
};
```

---

### 階段 5: 重試佇列

```typescript
// src/lib/webhook/queue.ts
import { Queue, Worker, Job } from 'bullmq';

const webhookQueue = new Queue('webhooks', {
  connection: {
    host: process.env.REDIS_HOST,
    port: parseInt(process.env.REDIS_PORT || '6379'),
  },
  defaultJobOptions: {
    attempts: 5,
    backoff: {
      type: 'exponential',
      delay: 1000,
    },
  },
});

// 加入佇列
export async function enqueueWebhook(event: WebhookEvent) {
  await webhookQueue.add(event.type, event, {
    jobId: event.id, // 確保冪等性
  });
}

// Worker 處理
const worker = new Worker(
  'webhooks',
  async (job: Job) => {
    const processor = getProcessor();
    await processor.process(job.data);
  },
  {
    connection: {
      host: process.env.REDIS_HOST,
      port: parseInt(process.env.REDIS_PORT || '6379'),
    },
  }
);

worker.on('completed', (job) => {
  console.log(`Job ${job.id} completed`);
});

worker.on('failed', (job, error) => {
  console.error(`Job ${job?.id} failed:`, error);
  // 發送告警
});
```

---

### 階段 5B: Spring Boot Webhook Endpoint

> 當 framework 為 `spring` 時使用

```java
// src/main/java/com/example/webhook/WebhookController.java
@RestController
@RequestMapping("/api/webhooks")
@Slf4j
public class WebhookController {

    private final WebhookProcessor webhookProcessor;
    private final WebhookEventRepository eventRepository;

    @PostMapping("/{provider}")
    public ResponseEntity<Map<String, String>> handleWebhook(
            @PathVariable String provider,
            @RequestBody String payload,
            @RequestHeader("X-Webhook-Signature") String signature) {

        // 1. 驗證簽名
        if (!webhookProcessor.verifySignature(provider, payload, signature)) {
            log.warn("Invalid webhook signature from provider: {}", provider);
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                    .body(Map.of("error", "Invalid signature"));
        }

        // 2. 解析事件
        WebhookEvent event = webhookProcessor.parseEvent(payload);

        // 3. 冪等性檢查
        if (eventRepository.existsByEventId(event.getId())) {
            return ResponseEntity.ok(Map.of("status", "already_processed"));
        }

        // 4. 非同步處理
        webhookProcessor.processAsync(event);

        // 5. 記錄事件
        eventRepository.save(WebhookEventEntity.from(event));

        return ResponseEntity.ok(Map.of("status", "accepted"));
    }
}
```

```java
// src/main/java/com/example/webhook/WebhookProcessor.java
@Service
@Slf4j
public class WebhookProcessor {

    @Value("${webhook.secret}")
    private String webhookSecret;

    private final Map<String, WebhookHandler> handlers = new ConcurrentHashMap<>();

    public boolean verifySignature(String provider, String payload, String signature) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(webhookSecret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            String expected = "sha256=" + Hex.encodeHexString(mac.doFinal(payload.getBytes(StandardCharsets.UTF_8)));
            return MessageDigest.isEqual(expected.getBytes(), signature.getBytes());
        } catch (Exception e) {
            log.error("Signature verification failed", e);
            return false;
        }
    }

    @Async
    public void processAsync(WebhookEvent event) {
        WebhookHandler handler = handlers.get(event.getType());
        if (handler != null) {
            handler.handle(event);
        } else {
            log.warn("No handler for event type: {}", event.getType());
        }
    }

    public void registerHandler(String eventType, WebhookHandler handler) {
        handlers.put(eventType, handler);
    }
}
```

---

### 階段 5C: FastAPI Webhook Endpoint

> 當 framework 為 `fastapi` 時使用

```python
# src/webhooks/router.py
from fastapi import APIRouter, Header, HTTPException, BackgroundTasks, Request
from typing import Optional
import hmac
import hashlib
import json
import logging

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = "sha256=" + hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

@router.post("/{provider}")
async def handle_webhook(
    provider: str,
    request: Request,
    background_tasks: BackgroundTasks,
    x_webhook_signature: Optional[str] = Header(None),
):
    payload = await request.body()

    # 1. 驗證簽名
    if not x_webhook_signature or not verify_signature(payload, x_webhook_signature, WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")

    event = json.loads(payload)

    # 2. 冪等性檢查
    if await is_event_processed(event.get("id")):
        return {"status": "already_processed"}

    # 3. 非同步處理
    background_tasks.add_task(process_webhook_event, provider, event)

    # 4. 記錄事件
    await mark_event_processed(event.get("id"))

    return {"status": "accepted"}

async def process_webhook_event(provider: str, event: dict):
    event_type = event.get("type", "unknown")
    handler = HANDLERS.get(event_type)
    if handler:
        await handler(event)
    else:
        logger.warning(f"No handler for event type: {event_type}")
```

---

### 階段 6: 驗證 🔴

**驗證清單**:
- [ ] 簽名驗證正確
- [ ] 事件處理成功
- [ ] 冪等性機制運作
- [ ] 重試機制正常
- [ ] 錯誤告警正確

**測試命令**:
```bash
# 發送測試 Webhook
curl -X POST http://localhost:3000/api/webhook \
  -H "Content-Type: application/json" \
  -H "x-webhook-signature: sha256=..." \
  -d '{"id": "evt_123", "type": "order.created", "data": {...}}'
```

🔴 **確認點**: 確認 Webhook 處理正常

---

## 產出物

| 產出物 | 路徑 |
|--------|------|
| Webhook 處理器 | `src/lib/webhook/processor.ts` |
| 事件處理器 | `src/lib/webhook/handlers/*.ts` |
| API Endpoint | `app/api/webhook/route.ts` |
| 佇列處理 | `src/lib/webhook/queue.ts` |

---

## 相關 Skill

- `/integration-stripe` - Stripe Webhook
- `/integration-api-client` - API 客戶端

---


## 相關檔案

- SOP 參考: `scenarios/integration/SOP_QuickRef.md`

**基於**: AISDLC v0.09 Integration 情境
