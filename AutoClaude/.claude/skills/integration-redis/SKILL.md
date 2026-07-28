---
name: integration-redis
description: 整合 Redis 快取服務，包含快取策略、Session、佇列
user-invocable: true
disable-model-invocation: false
argument-hint: "[feature: 功能 (cache/session/queue/pubsub)] [framework: 框架 (ioredis/spring-data-redis/redis-py)]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
  - Bash
---

# Integration Redis Skill

整合 Redis 快取和資料結構服務。

---

## 觸發方式

```bash
/integration-redis               # 基本快取
/integration-redis session       # Session 管理
/integration-redis queue         # 任務佇列
/integration-redis pubsub        # 發布訂閱
```

---

## 執行流程

### 階段 1: Redis 設定 🔴

**確認項目**:
- [ ] Redis 伺服器資訊
- [ ] 使用情境 (快取/Session/佇列)
- [ ] 資料過期策略
- [ ] 叢集配置 (可選)

**環境變數**:
```env
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your-password  # 可選
```

🔴 **確認點**: 確認 Redis 配置

---

### 階段 2: Redis 客戶端

```typescript
// src/lib/redis/client.ts
import Redis from 'ioredis';

const globalForRedis = globalThis as unknown as {
  redis: Redis | undefined;
};

export const redis =
  globalForRedis.redis ??
  new Redis(process.env.REDIS_URL!, {
    maxRetriesPerRequest: 3,
    lazyConnect: true,
  });

if (process.env.NODE_ENV !== 'production') {
  globalForRedis.redis = redis;
}

// 連線事件
redis.on('connect', () => console.log('Redis connected'));
redis.on('error', (err) => console.error('Redis error:', err));
```

---

### 階段 3: 快取服務

```typescript
// src/lib/redis/cache.ts
import { redis } from './client';

interface CacheOptions {
  ttl?: number; // 秒
  prefix?: string;
}

const DEFAULT_TTL = 3600; // 1 小時
const CACHE_PREFIX = 'cache:';

export const cacheService = {
  // 取得快取
  async get<T>(key: string, options: CacheOptions = {}): Promise<T | null> {
    const fullKey = (options.prefix || CACHE_PREFIX) + key;
    const data = await redis.get(fullKey);
    return data ? JSON.parse(data) : null;
  },

  // 設定快取
  async set<T>(key: string, value: T, options: CacheOptions = {}): Promise<void> {
    const fullKey = (options.prefix || CACHE_PREFIX) + key;
    const ttl = options.ttl ?? DEFAULT_TTL;
    await redis.setex(fullKey, ttl, JSON.stringify(value));
  },

  // 取得或設定 (Cache-Aside Pattern)
  async getOrSet<T>(
    key: string,
    fetcher: () => Promise<T>,
    options: CacheOptions = {}
  ): Promise<T> {
    const cached = await this.get<T>(key, options);
    if (cached !== null) {
      return cached;
    }

    const data = await fetcher();
    await this.set(key, data, options);
    return data;
  },

  // 刪除快取
  async del(key: string, options: CacheOptions = {}): Promise<void> {
    const fullKey = (options.prefix || CACHE_PREFIX) + key;
    await redis.del(fullKey);
  },

  // 批量刪除 (使用 pattern)
  async delPattern(pattern: string): Promise<number> {
    const keys = await redis.keys(CACHE_PREFIX + pattern);
    if (keys.length === 0) return 0;
    return redis.del(...keys);
  },

  // 清除所有快取
  async flush(): Promise<void> {
    const keys = await redis.keys(CACHE_PREFIX + '*');
    if (keys.length > 0) {
      await redis.del(...keys);
    }
  },

  // 檢查是否存在
  async exists(key: string, options: CacheOptions = {}): Promise<boolean> {
    const fullKey = (options.prefix || CACHE_PREFIX) + key;
    return (await redis.exists(fullKey)) === 1;
  },

  // 更新 TTL
  async touch(key: string, ttl: number, options: CacheOptions = {}): Promise<void> {
    const fullKey = (options.prefix || CACHE_PREFIX) + key;
    await redis.expire(fullKey, ttl);
  },
};
```

---

### 階段 4: Session 管理

```typescript
// src/lib/redis/session.ts
import { redis } from './client';
import { v4 as uuidv4 } from 'uuid';

interface SessionData {
  userId: string;
  email: string;
  role: string;
  [key: string]: unknown;
}

const SESSION_PREFIX = 'session:';
const SESSION_TTL = 86400; // 24 小時

export const sessionService = {
  // 建立 Session
  async create(data: SessionData): Promise<string> {
    const sessionId = uuidv4();
    await redis.setex(
      SESSION_PREFIX + sessionId,
      SESSION_TTL,
      JSON.stringify(data)
    );
    return sessionId;
  },

  // 取得 Session
  async get(sessionId: string): Promise<SessionData | null> {
    const data = await redis.get(SESSION_PREFIX + sessionId);
    return data ? JSON.parse(data) : null;
  },

  // 更新 Session
  async update(sessionId: string, data: Partial<SessionData>): Promise<void> {
    const existing = await this.get(sessionId);
    if (!existing) throw new Error('Session not found');

    await redis.setex(
      SESSION_PREFIX + sessionId,
      SESSION_TTL,
      JSON.stringify({ ...existing, ...data })
    );
  },

  // 延長 Session
  async refresh(sessionId: string): Promise<void> {
    await redis.expire(SESSION_PREFIX + sessionId, SESSION_TTL);
  },

  // 刪除 Session
  async destroy(sessionId: string): Promise<void> {
    await redis.del(SESSION_PREFIX + sessionId);
  },

  // 刪除使用者所有 Session
  async destroyUserSessions(userId: string): Promise<void> {
    const keys = await redis.keys(SESSION_PREFIX + '*');
    for (const key of keys) {
      const data = await redis.get(key);
      if (data) {
        const session = JSON.parse(data);
        if (session.userId === userId) {
          await redis.del(key);
        }
      }
    }
  },
};
```

---

### 階段 5: 任務佇列

```typescript
// src/lib/redis/queue.ts
import { redis } from './client';

interface Job<T = unknown> {
  id: string;
  type: string;
  data: T;
  attempts: number;
  maxAttempts: number;
  createdAt: number;
}

const QUEUE_PREFIX = 'queue:';

export function createQueue(queueName: string) {
  const key = QUEUE_PREFIX + queueName;
  const processingKey = key + ':processing';
  const failedKey = key + ':failed';

  return {
    // 加入佇列
    async add<T>(type: string, data: T, maxAttempts = 3): Promise<string> {
      const job: Job<T> = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        type,
        data,
        attempts: 0,
        maxAttempts,
        createdAt: Date.now(),
      };
      await redis.lpush(key, JSON.stringify(job));
      return job.id;
    },

    // 取出任務
    async take(): Promise<Job | null> {
      const data = await redis.brpoplpush(key, processingKey, 0);
      return data ? JSON.parse(data) : null;
    },

    // 完成任務
    async complete(job: Job): Promise<void> {
      await redis.lrem(processingKey, 1, JSON.stringify(job));
    },

    // 任務失敗
    async fail(job: Job, error: string): Promise<void> {
      job.attempts++;

      if (job.attempts < job.maxAttempts) {
        // 重新加入佇列
        await redis.lrem(processingKey, 1, JSON.stringify({ ...job, attempts: job.attempts - 1 }));
        await redis.lpush(key, JSON.stringify(job));
      } else {
        // 移至失敗佇列
        await redis.lrem(processingKey, 1, JSON.stringify({ ...job, attempts: job.attempts - 1 }));
        await redis.lpush(failedKey, JSON.stringify({ ...job, error }));
      }
    },

    // 取得佇列長度
    async length(): Promise<number> {
      return redis.llen(key);
    },

    // 取得處理中任務數
    async processingCount(): Promise<number> {
      return redis.llen(processingKey);
    },
  };
}

// 使用範例
export const emailQueue = createQueue('emails');
export const notificationQueue = createQueue('notifications');
```

---

### 階段 6: 發布訂閱

```typescript
// src/lib/redis/pubsub.ts
import Redis from 'ioredis';

// 訂閱需要獨立連線
const subscriber = new Redis(process.env.REDIS_URL!);
const publisher = new Redis(process.env.REDIS_URL!);

type MessageHandler = (message: string, channel: string) => void;
const handlers = new Map<string, Set<MessageHandler>>();

subscriber.on('message', (channel, message) => {
  const channelHandlers = handlers.get(channel);
  if (channelHandlers) {
    channelHandlers.forEach((handler) => handler(message, channel));
  }
});

export const pubsub = {
  // 發布
  async publish(channel: string, message: unknown): Promise<void> {
    await publisher.publish(channel, JSON.stringify(message));
  },

  // 訂閱
  subscribe(channel: string, handler: MessageHandler): () => void {
    if (!handlers.has(channel)) {
      handlers.set(channel, new Set());
      subscriber.subscribe(channel);
    }
    handlers.get(channel)!.add(handler);

    // 返回取消訂閱函數
    return () => {
      const channelHandlers = handlers.get(channel);
      if (channelHandlers) {
        channelHandlers.delete(handler);
        if (channelHandlers.size === 0) {
          handlers.delete(channel);
          subscriber.unsubscribe(channel);
        }
      }
    };
  },
};
```

---

### 階段 6B: Python Redis 客戶端 (redis-py)

> 當 framework 為 `redis-py` 時使用

**安裝依賴**:
```bash
pip install 'redis[hiredis]'
```

```python
# src/lib/redis_client.py
import redis.asyncio as aioredis
import json
from typing import TypeVar, Optional, Callable, Awaitable
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")

class RedisClient:
    def __init__(self, url: str = "redis://localhost:6379"):
        self.redis = aioredis.from_url(url, decode_responses=True)

    # === 快取服務 ===
    async def cache_get(self, key: str, prefix: str = "cache:") -> Optional[dict]:
        data = await self.redis.get(f"{prefix}{key}")
        return json.loads(data) if data else None

    async def cache_set(self, key: str, value: dict, ttl: int = 3600, prefix: str = "cache:"):
        await self.redis.setex(f"{prefix}{key}", ttl, json.dumps(value))

    async def cache_get_or_set(
        self, key: str, fetcher: Callable[[], Awaitable[dict]], ttl: int = 3600
    ) -> dict:
        cached = await self.cache_get(key)
        if cached is not None:
            return cached
        data = await fetcher()
        await self.cache_set(key, data, ttl)
        return data

    async def cache_delete(self, key: str, prefix: str = "cache:"):
        await self.redis.delete(f"{prefix}{key}")

    # === Session 服務 ===
    async def session_create(self, session_id: str, data: dict, ttl: int = 86400):
        await self.redis.setex(f"session:{session_id}", ttl, json.dumps(data))

    async def session_get(self, session_id: str) -> Optional[dict]:
        data = await self.redis.get(f"session:{session_id}")
        return json.loads(data) if data else None

    async def session_destroy(self, session_id: str):
        await self.redis.delete(f"session:{session_id}")

    # === Pub/Sub ===
    async def publish(self, channel: str, message: dict):
        await self.redis.publish(channel, json.dumps(message))

    async def subscribe(self, channel: str):
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        return pubsub

    async def close(self):
        await self.redis.aclose()
```

---

### 階段 6C: Java/Spring Boot Redis 客戶端 (Spring Data Redis)

> 當 framework 為 `spring-data-redis` 時使用

**安裝依賴** (`build.gradle.kts`):
```kotlin
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-data-redis")
    implementation("com.fasterxml.jackson.core:jackson-databind")
}
```

**配置**: `application.yml`
```yaml
spring:
  data:
    redis:
      host: ${REDIS_HOST:localhost}
      port: ${REDIS_PORT:6379}
      password: ${REDIS_PASSWORD:}
      timeout: 5000ms
```

```java
// src/main/java/com/example/redis/RedisCacheService.java
@Service
@Slf4j
public class RedisCacheService {

    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;

    private static final String CACHE_PREFIX = "cache:";
    private static final long DEFAULT_TTL = 3600; // 秒

    public RedisCacheService(StringRedisTemplate redisTemplate, ObjectMapper objectMapper) {
        this.redisTemplate = redisTemplate;
        this.objectMapper = objectMapper;
    }

    // 快取讀取
    public <T> Optional<T> get(String key, Class<T> type) {
        String data = redisTemplate.opsForValue().get(CACHE_PREFIX + key);
        if (data == null) return Optional.empty();
        try {
            return Optional.of(objectMapper.readValue(data, type));
        } catch (JsonProcessingException e) {
            log.error("Cache deserialization failed for key: {}", key, e);
            return Optional.empty();
        }
    }

    // 快取寫入
    public <T> void set(String key, T value, long ttlSeconds) {
        try {
            String json = objectMapper.writeValueAsString(value);
            redisTemplate.opsForValue().set(
                CACHE_PREFIX + key, json, Duration.ofSeconds(ttlSeconds)
            );
        } catch (JsonProcessingException e) {
            log.error("Cache serialization failed for key: {}", key, e);
        }
    }

    // Cache-Aside Pattern
    public <T> T getOrSet(String key, Class<T> type, Supplier<T> fetcher, long ttlSeconds) {
        return get(key, type).orElseGet(() -> {
            T data = fetcher.get();
            set(key, data, ttlSeconds);
            return data;
        });
    }

    // 刪除快取
    public void delete(String key) {
        redisTemplate.delete(CACHE_PREFIX + key);
    }
}
```

```java
// src/main/java/com/example/redis/RedisSessionService.java
@Service
public class RedisSessionService {

    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;
    private static final String SESSION_PREFIX = "session:";
    private static final long SESSION_TTL = 86400; // 24 小時

    public RedisSessionService(StringRedisTemplate redisTemplate, ObjectMapper objectMapper) {
        this.redisTemplate = redisTemplate;
        this.objectMapper = objectMapper;
    }

    public void create(String sessionId, Map<String, Object> data) throws JsonProcessingException {
        redisTemplate.opsForValue().set(
            SESSION_PREFIX + sessionId,
            objectMapper.writeValueAsString(data),
            Duration.ofSeconds(SESSION_TTL)
        );
    }

    public Optional<Map<String, Object>> get(String sessionId) {
        String data = redisTemplate.opsForValue().get(SESSION_PREFIX + sessionId);
        if (data == null) return Optional.empty();
        try {
            return Optional.of(objectMapper.readValue(data, new TypeReference<>() {}));
        } catch (JsonProcessingException e) {
            return Optional.empty();
        }
    }

    public void destroy(String sessionId) {
        redisTemplate.delete(SESSION_PREFIX + sessionId);
    }
}
```

---

### 階段 7: 驗證 🔴

**驗證清單**:
- [ ] Redis 連線正常
- [ ] 快取讀寫正常
- [ ] Session 管理正確
- [ ] 佇列處理正常
- [ ] 發布訂閱運作

🔴 **確認點**: 確認 Redis 整合正常

---

## 產出物

| 產出物 | 路徑 |
|--------|------|
| Redis 客戶端 | `src/lib/redis/client.ts` |
| 快取服務 | `src/lib/redis/cache.ts` |
| Session 服務 | `src/lib/redis/session.ts` |
| 佇列服務 | `src/lib/redis/queue.ts` |
| PubSub 服務 | `src/lib/redis/pubsub.ts` |

---

## 相關 Skill

- `/integration-database` - 資料庫整合
- `/performance` - 效能優化

---


## 相關檔案

- SOP 參考: `scenarios/integration/SOP_QuickRef.md`

**基於**: AISDLC v0.09 Integration 情境
