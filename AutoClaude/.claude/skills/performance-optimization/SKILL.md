---
name: performance
description: 效能分析與優化，識別瓶頸並提供改善方案
user-invocable: true
disable-model-invocation: false
argument-hint: "[focus: 優化重點 (frontend/backend/database/full)]"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# Performance Optimization Skill

基於 AISDLC Performance 情境的效能優化技能。

---

## 觸發方式

```bash
/performance               # 完整效能分析
/performance frontend      # 前端效能優化
/performance backend       # 後端效能優化
/performance database      # 資料庫效能優化
```

---

## 執行流程

### 階段 1: 效能基準測量 (15分鐘)

**前端指標**:
```bash
# Lighthouse 分析
npx lighthouse https://your-site.com --output=json --output-path=./lighthouse.json

# Bundle 分析
npx webpack-bundle-analyzer stats.json
```

**關鍵指標**:
| 指標 | 良好 | 需改善 | 差 |
|------|------|--------|-----|
| LCP | < 2.5s | 2.5-4s | > 4s |
| FID | < 100ms | 100-300ms | > 300ms |
| CLS | < 0.1 | 0.1-0.25 | > 0.25 |
| TTI | < 3.8s | 3.8-7.3s | > 7.3s |

**後端指標**:
| 指標 | 良好 | 需改善 | 差 |
|------|------|--------|-----|
| Response Time (P95) | < 200ms | 200-500ms | > 500ms |
| Throughput | > 1000 RPS | 500-1000 RPS | < 500 RPS |
| Error Rate | < 0.1% | 0.1-1% | > 1% |

---

### 階段 2: 瓶頸識別 🔴

**常見瓶頸類型**:

#### 前端瓶頸
| 問題 | 症狀 | 診斷方法 |
|------|------|---------|
| Bundle 過大 | 首次載入慢 | Webpack Bundle Analyzer |
| 未優化圖片 | LCP 高 | Lighthouse |
| 阻塞渲染 | FCP 高 | Chrome DevTools |
| 記憶體洩漏 | 越用越慢 | Memory Profiler |

#### 後端瓶頸
| 問題 | 症狀 | 診斷方法 |
|------|------|---------|
| N+1 查詢 | 回應時間高 | Query Log |
| 缺少索引 | DB 查詢慢 | EXPLAIN ANALYZE |
| 無快取 | 重複計算 | APM 工具 |
| 同步阻塞 | 並發低 | Load Test |

🔴 **確認點**: 確認優先處理的瓶頸

---

### 階段 3: 優化方案

#### 前端優化

**1. 代碼分割**:
```typescript
// Before
import { HeavyComponent } from './HeavyComponent';

// After
const HeavyComponent = lazy(() => import('./HeavyComponent'));

function App() {
  return (
    <Suspense fallback={<Loading />}>
      <HeavyComponent />
    </Suspense>
  );
}
```

**2. 圖片優化**:
```typescript
// Next.js Image
import Image from 'next/image';

<Image
  src="/hero.jpg"
  width={1200}
  height={600}
  priority
  placeholder="blur"
/>
```

**3. 快取策略**:
```typescript
// React Query 快取
const { data } = useQuery({
  queryKey: ['users'],
  queryFn: fetchUsers,
  staleTime: 5 * 60 * 1000, // 5 分鐘
  cacheTime: 30 * 60 * 1000, // 30 分鐘
});
```

#### 後端優化

**1. 資料庫查詢**:
```sql
-- 新增索引
CREATE INDEX idx_users_email ON users(email);

-- 避免 SELECT *
SELECT id, name, email FROM users WHERE status = 'active';
```

**2. N+1 問題**:
```typescript
// Before: N+1
const users = await User.findAll();
for (const user of users) {
  user.orders = await Order.findAll({ where: { userId: user.id } });
}

// After: Eager Loading
const users = await User.findAll({
  include: [{ model: Order }],
});
```

**3. 快取層**:
```typescript
import Redis from 'ioredis';

const redis = new Redis();

async function getUser(id: string) {
  const cached = await redis.get(`user:${id}`);
  if (cached) return JSON.parse(cached);

  const user = await db.user.findUnique({ where: { id } });
  await redis.setex(`user:${id}`, 3600, JSON.stringify(user));
  return user;
}
```

---

### 階段 4: 驗證改善

**測量指令**:
```bash
# 前端
npx lighthouse https://your-site.com --output=html

# 後端負載測試
npx autocannon -c 100 -d 30 http://localhost:3000/api/users
```

**成效報告**:
```markdown
## 效能優化成效

### 前端
| 指標 | 優化前 | 優化後 | 改善 |
|------|--------|--------|------|
| LCP | 4.2s | 1.8s | ⬇️ 57% |
| Bundle Size | 850KB | 320KB | ⬇️ 62% |

### 後端
| 指標 | 優化前 | 優化後 | 改善 |
|------|--------|--------|------|
| P95 Response | 450ms | 120ms | ⬇️ 73% |
| Throughput | 500 RPS | 2000 RPS | ⬆️ 300% |
```

---

## 產出物

| 產出物 | 說明 |
|--------|------|
| 效能分析報告 | 瓶頸識別和基準數據 |
| 優化方案 | 具體改善建議 |
| 成效報告 | 優化前後比對 |

---


## 相關檔案

- SOP 參考: `scenarios/performance/SOP_QuickRef.md`

**基於**: AISDLC v0.09 Performance 情境
