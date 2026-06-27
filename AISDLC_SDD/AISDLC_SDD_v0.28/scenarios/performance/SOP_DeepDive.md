# Performance Optimization 效能優化 - 深度技術指南
# Deep Dive Technical Guide

**版本**: v0.01
**最後更新**: 2026-02-17
**適用對象**: 經驗豐富的效能工程師、系統架構師、資深開發者
**建議閱讀**: 先閱讀 SOP_QuickRef.md 和 SOP.md
**文檔類型**: 技術參考、最佳實踐、深度分析

---

## 📚 文檔說明

### 何時閱讀此文檔

✅ **適合閱讀的情況**:
- 處理大規模系統的效能瓶頸
- 需要進行深度效能分析和調優
- 設計高併發、低延遲系統
- 處理資料庫查詢效能問題
- 優化前端載入速度和用戶體驗
- 進行系統容量規劃

❌ **不建議閱讀的情況**:
- 初次進行效能優化(請閱讀 SOP.md)
- 快速參考優化步驟(請閱讀 SOP_QuickRef.md)
- 簡單的代碼優化

### 文檔結構

```
Part 1: 效能分析方法論
Part 2: 前端效能優化深度技術
Part 3: 後端效能優化策略
Part 4: 資料庫效能調優
Part 5: 網路層優化
Part 6: 快取策略深度解析
Part 7: 併發與並行優化
Part 8: 效能監控與可觀測性
Part 9: 容量規劃與擴展
Part 10: 真實案例研究
```

---

## Part 1: 效能分析方法論

### 1.1 USE 方法 (Utilization, Saturation, Errors)

**適用於**: 系統資源分析

```yaml
USE 方法檢查清單:

For each resource (CPU, Memory, Disk, Network):

Utilization (使用率):
  - CPU: top, mpstat, sar
  - Memory: free, vmstat
  - Disk I/O: iostat, iotop
  - Network: ifconfig, netstat, sar

Saturation (飽和度):
  - CPU: vmstat (r > CPU count)
  - Memory: vmstat (si, so)
  - Disk: iostat (avgqu-sz)
  - Network: netstat (dropped packets)

Errors (錯誤):
  - CPU: dmesg, /var/log/messages
  - Memory: dmesg (OOM messages)
  - Disk: dmesg, smartctl
  - Network: ifconfig (errors, dropped)
```

**實戰範例**:

```bash
# CPU 使用率和飽和度
mpstat -P ALL 1

# CPU: 00:00:01     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
# 00:00:02     all   45.00    0.00   10.00    5.00    0.00    0.00    0.00    0.00    0.00   40.00

# 記憶體使用率
free -m
#               total        used        free      shared  buff/cache   available
# Mem:          16000       12000        1000         500        3000        3500
# Swap:          8000        2000        6000

# Swap 使用表示記憶體可能飽和

# Disk I/O 飽和度
iostat -x 1
# Device    r/s   w/s   rkB/s   wkB/s  avgqu-sz  await  svctm  %util
# sda      100    50    4000    2000      15.0   150ms   10ms   95%

# avgqu-sz > 1 且 %util 接近 100% 表示磁碟飽和

# 網路錯誤
netstat -i
# Iface   MTU  RX-OK RX-ERR RX-DRP  TX-OK TX-ERR TX-DRP
# eth0   1500  1000000    100     50  900000     10     20

# RX-ERR, TX-ERR 表示網路錯誤
```

### 1.2 RED 方法 (Rate, Errors, Duration)

**適用於**: 微服務和請求驅動系統

```yaml
RED Metrics:

Rate (請求速率):
  - 每秒請求數 (RPS)
  - 每分鐘請求數 (RPM)

Errors (錯誤率):
  - HTTP 5xx 錯誤率
  - 應用程式異常率

Duration (響應時間):
  - P50 (中位數)
  - P95 (95 百分位)
  - P99 (99 百分位)
```

**Prometheus + Grafana 實作**:

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'api-server'
    static_configs:
      - targets: ['localhost:8080']
```

```javascript
// 應用程式埋點 (Node.js + prom-client)
const promClient = require('prom-client');
const express = require('express');

const app = express();

// 建立 RED metrics
const httpRequestDuration = new promClient.Histogram({
  name: 'http_request_duration_seconds',
  help: 'Duration of HTTP requests in seconds',
  labelNames: ['method', 'route', 'status_code'],
  buckets: [0.1, 0.5, 1, 2, 5]
});

const httpRequestTotal = new promClient.Counter({
  name: 'http_requests_total',
  help: 'Total number of HTTP requests',
  labelNames: ['method', 'route', 'status_code']
});

// Middleware
app.use((req, res, next) => {
  const start = Date.now();

  res.on('finish', () => {
    const duration = (Date.now() - start) / 1000;

    httpRequestDuration
      .labels(req.method, req.route?.path || req.path, res.statusCode)
      .observe(duration);

    httpRequestTotal
      .labels(req.method, req.route?.path || req.path, res.statusCode)
      .inc();
  });

  next();
});

// Metrics endpoint
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', promClient.register.contentType);
  res.end(await promClient.register.metrics());
});

app.listen(8080);
```

### 1.3 Flamegraph 火焰圖分析

```bash
# Node.js Flamegraph 生成
# 1. 使用 clinic.js
npm install -g clinic
clinic flame -- node app.js

# 2. 使用 0x
npm install -g 0x
0x app.js

# 3. 使用 perf (Linux)
# 收集數據
perf record -F 99 -p <PID> -g -- sleep 30

# 生成火焰圖
perf script | stackcollapse-perf.pl | flamegraph.pl > flamegraph.svg
```

---

## Part 2: 前端效能優化深度技術

### 2.1 關鍵渲染路徑優化 (Critical Rendering Path)

**理解 CRP**:

```yaml
Critical Rendering Path 階段:

1. 構建 DOM Tree
   HTML → Parser → DOM

2. 構建 CSSOM Tree
   CSS → Parser → CSSOM

3. 執行 JavaScript
   可能修改 DOM/CSSOM

4. 構建 Render Tree
   DOM + CSSOM → Render Tree

5. Layout (排版)
   計算元素位置和尺寸

6. Paint (繪製)
   繪製像素到螢幕
```

**優化策略**:

```html
<!-- ❌ 阻塞渲染的 CSS -->
<head>
  <link rel="stylesheet" href="styles.css">
  <link rel="stylesheet" href="print.css">
</head>

<!-- ✅ 優化後 -->
<head>
  <!-- Critical CSS 內聯 -->
  <style>
    /* 首屏關鍵 CSS */
    body { margin: 0; font-family: sans-serif; }
    .header { height: 60px; background: #333; }
  </style>

  <!-- 非關鍵 CSS 延遲載入 -->
  <link rel="preload" href="styles.css" as="style" onload="this.onload=null;this.rel='stylesheet'">
  <noscript><link rel="stylesheet" href="styles.css"></noscript>

  <!-- 媒體查詢避免阻塞 -->
  <link rel="stylesheet" href="print.css" media="print">
</head>

<!-- ❌ 阻塞解析的 JavaScript -->
<head>
  <script src="analytics.js"></script>
  <script src="app.js"></script>
</head>

<!-- ✅ 優化後 -->
<head>
  <!-- 關鍵 JS 使用 defer -->
  <script defer src="app.js"></script>

  <!-- 非關鍵 JS 使用 async -->
  <script async src="analytics.js"></script>
</head>

<!-- 或使用動態載入 -->
<script>
  // 在頁面載入後動態載入非關鍵腳本
  window.addEventListener('load', () => {
    const script = document.createElement('script');
    script.src = 'non-critical.js';
    document.body.appendChild(script);
  });
</script>
```

### 2.2 JavaScript 效能優化

**避免長任務 (Long Tasks)**:

```javascript
// ❌ 長任務阻塞主執行緒
function processLargeDataset(data) {
  const result = [];
  for (let i = 0; i < data.length; i++) {
    // 複雜計算
    const processed = complexOperation(data[i]);
    result.push(processed);
  }
  return result;
}

// 如果 data.length = 10000, 可能阻塞主執行緒數秒

// ✅ 使用時間分片 (Time Slicing)
function processLargeDataset(data, callback) {
  const chunkSize = 100;
  let index = 0;
  const result = [];

  function processChunk() {
    const end = Math.min(index + chunkSize, data.length);

    for (let i = index; i < end; i++) {
      const processed = complexOperation(data[i]);
      result.push(processed);
    }

    index = end;

    if (index < data.length) {
      // 使用 requestIdleCallback 在瀏覽器空閒時處理
      requestIdleCallback(processChunk, { timeout: 1000 });
    } else {
      callback(result);
    }
  }

  processChunk();
}

// ✅ 使用 Web Workers 處理 CPU 密集任務
// main.js
const worker = new Worker('processor.worker.js');

worker.postMessage({ data: largeDataset });

worker.onmessage = (e) => {
  const result = e.data;
  console.log('Processed:', result);
};

// processor.worker.js
self.onmessage = (e) => {
  const { data } = e.data;
  const result = [];

  for (let i = 0; i < data.length; i++) {
    result.push(complexOperation(data[i]));
  }

  self.postMessage(result);
};
```

**記憶體優化**:

```javascript
// ❌ 記憶體洩漏
class ImageGallery {
  constructor() {
    this.images = [];
    this.loadImages();

    // 事件監聽器未清除
    window.addEventListener('resize', this.handleResize.bind(this));
  }

  loadImages() {
    for (let i = 0; i < 1000; i++) {
      const img = new Image();
      img.src = `image-${i}.jpg`;
      this.images.push(img); // 永久保存所有圖片
    }
  }

  handleResize() {
    this.loadImages(); // 每次 resize 都載入新圖片!
  }
}

// ✅ 優化後
class ImageGallery {
  constructor() {
    this.images = new Map(); // 使用 Map 便於管理
    this.loadImages();

    this.handleResize = this.handleResize.bind(this);
    window.addEventListener('resize', this.handleResize);
  }

  loadImages() {
    // 只載入可見範圍的圖片
    const visibleRange = this.getVisibleRange();

    for (let i = visibleRange.start; i < visibleRange.end; i++) {
      if (!this.images.has(i)) {
        const img = new Image();
        img.src = `image-${i}.jpg`;
        this.images.set(i, img);
      }
    }

    // 清除不可見的圖片
    this.images.forEach((img, index) => {
      if (index < visibleRange.start || index >= visibleRange.end) {
        this.images.delete(index);
      }
    });
  }

  handleResize() {
    this.loadImages();
  }

  destroy() {
    // 清理事件監聽器
    window.removeEventListener('resize', this.handleResize);
    this.images.clear();
  }
}
```

### 2.3 資源載入優化

**Resource Hints**:

```html
<!-- DNS Prefetch: 提前解析 DNS -->
<link rel="dns-prefetch" href="https://api.example.com">

<!-- Preconnect: 提前建立連接 (DNS + TCP + TLS) -->
<link rel="preconnect" href="https://cdn.example.com">

<!-- Prefetch: 預載入未來可能需要的資源 -->
<link rel="prefetch" href="/page-2.html">

<!-- Preload: 高優先級載入當前頁面需要的資源 -->
<link rel="preload" href="critical.css" as="style">
<link rel="preload" href="hero.jpg" as="image">
<link rel="preload" href="font.woff2" as="font" type="font/woff2" crossorigin>

<!-- Prerender: 預渲染整個頁面 (慎用) -->
<link rel="prerender" href="/next-page.html">
```

**圖片優化**:

```html
<!-- 使用現代圖片格式 -->
<picture>
  <!-- WebP for browsers that support it -->
  <source srcset="image.webp" type="image/webp">

  <!-- AVIF for even better compression -->
  <source srcset="image.avif" type="image/avif">

  <!-- Fallback to JPEG -->
  <img src="image.jpg" alt="Description">
</picture>

<!-- 響應式圖片 -->
<img
  srcset="
    image-320w.jpg 320w,
    image-640w.jpg 640w,
    image-1280w.jpg 1280w
  "
  sizes="
    (max-width: 320px) 280px,
    (max-width: 640px) 600px,
    1200px
  "
  src="image-640w.jpg"
  alt="Description"
>

<!-- 延遲載入 -->
<img src="image.jpg" loading="lazy" alt="Description">
```

---

## Part 3: 後端效能優化策略

### 3.1 非同步處理模式

**Node.js 非同步最佳實踐**:

```javascript
// ❌ 同步阻塞
const fs = require('fs');

app.get('/data', (req, res) => {
  const data = fs.readFileSync('/large-file.json'); // 阻塞!
  res.json(JSON.parse(data));
});

// ✅ 非同步非阻塞
const fs = require('fs').promises;

app.get('/data', async (req, res) => {
  try {
    const data = await fs.readFile('/large-file.json', 'utf8');
    res.json(JSON.parse(data));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ✅ 串流處理 (處理大文件)
const fs = require('fs');

app.get('/download', (req, res) => {
  const stream = fs.createReadStream('/very-large-file.zip');

  res.setHeader('Content-Type', 'application/zip');
  res.setHeader('Content-Disposition', 'attachment; filename="file.zip"');

  stream.pipe(res);
});
```

**並行處理**:

```javascript
// ❌ 串行執行 (慢)
async function getUserData(userId) {
  const user = await fetchUser(userId);          // 100ms
  const orders = await fetchOrders(userId);      // 150ms
  const preferences = await fetchPreferences(userId); // 50ms

  return { user, orders, preferences };
  // 總時間: 300ms
}

// ✅ 並行執行 (快)
async function getUserData(userId) {
  const [user, orders, preferences] = await Promise.all([
    fetchUser(userId),
    fetchOrders(userId),
    fetchPreferences(userId)
  ]);

  return { user, orders, preferences };
  // 總時間: 150ms (最慢的那個)
}

// ✅ 並行執行 + 錯誤處理
async function getUserData(userId) {
  const results = await Promise.allSettled([
    fetchUser(userId),
    fetchOrders(userId),
    fetchPreferences(userId)
  ]);

  return {
    user: results[0].status === 'fulfilled' ? results[0].value : null,
    orders: results[1].status === 'fulfilled' ? results[1].value : [],
    preferences: results[2].status === 'fulfilled' ? results[2].value : {}
  };
}
```

### 3.2 連接池優化

```javascript
// PostgreSQL 連接池配置
const { Pool } = require('pg');

const pool = new Pool({
  host: 'localhost',
  database: 'mydb',
  user: 'user',
  password: 'password',

  // 連接池配置
  max: 20,                    // 最大連接數
  min: 5,                     // 最小連接數
  idleTimeoutMillis: 30000,   // 空閒連接 30 秒後釋放
  connectionTimeoutMillis: 2000, // 獲取連接超時

  // 監控
  log: (msg) => console.log('Pool:', msg)
});

// 監控連接池狀態
setInterval(() => {
  console.log('Pool status:', {
    total: pool.totalCount,
    idle: pool.idleCount,
    waiting: pool.waitingCount
  });
}, 60000);

// 正確使用連接池
async function queryUser(userId) {
  const client = await pool.connect();

  try {
    const result = await client.query('SELECT * FROM users WHERE id = $1', [userId]);
    return result.rows[0];
  } finally {
    client.release(); // 必須釋放!
  }
}

// 或使用 pool.query (自動管理連接)
async function queryUser(userId) {
  const result = await pool.query('SELECT * FROM users WHERE id = $1', [userId]);
  return result.rows[0];
}
```

---

## Part 4: 資料庫效能調優

### 4.1 索引優化策略

```sql
-- 查詢分析
EXPLAIN ANALYZE
SELECT u.name, o.total
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE u.created_at > '2024-01-01'
  AND o.status = 'completed'
ORDER BY o.total DESC
LIMIT 10;

-- 結果分析
-- Seq Scan on users  (cost=0.00..1000.00 rows=10000 width=50) (actual time=0.05..25.30 rows=5000 loops=1)
--   Filter: (created_at > '2024-01-01'::date)
-- Seq Scan on orders  (cost=0.00..2000.00 rows=20000 width=20) (actual time=0.10..40.50 rows=15000 loops=1)
--   Filter: (status = 'completed'::text)

-- 問題: Seq Scan (全表掃描) - 慢!

-- 解決方案 1: 添加索引
CREATE INDEX idx_users_created_at ON users(created_at);
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);

-- 再次執行 EXPLAIN ANALYZE
-- Index Scan using idx_users_created_at on users  (actual time=0.01..5.20 rows=5000 loops=1)
-- Index Scan using idx_orders_user_id on orders  (actual time=0.02..8.30 rows=15000 loops=1)

-- 效能提升 5-10 倍!

-- 解決方案 2: 複合索引 (Composite Index)
CREATE INDEX idx_orders_user_status ON orders(user_id, status);

-- 可以同時滿足 user_id 和 status 查詢

-- 解決方案 3: 覆蓋索引 (Covering Index)
CREATE INDEX idx_orders_covering ON orders(user_id, status, total);

-- Index-only scan (不需要回表查詢)
```

**索引使用準則**:

```yaml
何時創建索引:

✅ WHERE 子句常用欄位
✅ JOIN 條件欄位
✅ ORDER BY 欄位
✅ GROUP BY 欄位
✅ 高選擇性欄位 (Cardinality 高)

❌ 何時不創建索引:

❌ 小型表 (< 1000 行)
❌ 頻繁更新的欄位
❌ 低選擇性欄位 (例如: boolean)
❌ 很少查詢的欄位

索引代價:

- 插入/更新/刪除變慢 (需要維護索引)
- 佔用額外儲存空間
- 過多索引反而降低效能
```

### 4.2 查詢優化技巧

```sql
-- ❌ N+1 查詢問題
-- 應用代碼:
users = SELECT * FROM users LIMIT 10;
for each user:
    orders = SELECT * FROM orders WHERE user_id = user.id;  -- N 次查詢!

-- ✅ 使用 JOIN 一次查詢
SELECT
  u.id,
  u.name,
  COALESCE(json_agg(
    json_build_object('id', o.id, 'total', o.total)
  ) FILTER (WHERE o.id IS NOT NULL), '[]') as orders
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE u.id IN (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
GROUP BY u.id, u.name;

-- ❌ SELECT * (查詢所有欄位)
SELECT * FROM users WHERE id = 1;

-- ✅ 只查詢需要的欄位
SELECT id, name, email FROM users WHERE id = 1;

-- ❌ 在 WHERE 中使用函數
SELECT * FROM users WHERE YEAR(created_at) = 2024;

-- ✅ 改寫為範圍查詢 (可使用索引)
SELECT * FROM users
WHERE created_at >= '2024-01-01'
  AND created_at < '2025-01-01';

-- ❌ OR 條件 (可能無法使用索引)
SELECT * FROM products WHERE category = 'electronics' OR price < 100;

-- ✅ 使用 UNION (可分別使用索引)
SELECT * FROM products WHERE category = 'electronics'
UNION
SELECT * FROM products WHERE price < 100;
```

---

## Part 5: 網路層優化

### 5.1 HTTP/2 和 HTTP/3

```yaml
HTTP/1.1 問題:

- Head-of-Line Blocking (隊頭阻塞)
- 每個請求需要獨立連接
- 無法優先級控制
- 文本協議 (較冗長)

HTTP/2 優勢:

✅ 多路復用 (Multiplexing) - 一個連接處理多個請求
✅ Header 壓縮 (HPACK)
✅ Server Push - 主動推送資源
✅ 請求優先級
✅ 二進制協議

HTTP/3 (QUIC) 優勢:

✅ 基於 UDP (更快建立連接)
✅ 0-RTT 連接恢復
✅ 改善的擁塞控制
✅ 連接遷移 (IP 變更不中斷)
```

**Nginx HTTP/2 配置**:

```nginx
server {
    listen 443 ssl http2;
    server_name example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # HTTP/2 Server Push
    location = /index.html {
        http2_push /styles.css;
        http2_push /script.js;
    }

    # 啟用 gzip 壓縮
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
    gzip_min_length 1000;

    # 快取靜態資源
    location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### 5.2 CDN 策略

```yaml
CDN 使用策略:

資源類型:
  - 靜態資源: JS, CSS, Images (必須使用 CDN)
  - 動態內容: 使用 Edge Computing

Cache-Control Headers:

Immutable 資源 (永不改變):
  Cache-Control: public, max-age=31536000, immutable

經常變更的資源:
  Cache-Control: public, max-age=3600, must-revalidate

私密資源:
  Cache-Control: private, max-age=0, no-cache

無快取:
  Cache-Control: no-store
```

---

## Part 6: 快取策略深度解析

### 6.1 多層快取架構

```yaml
快取層級 (由近到遠):

L1: 瀏覽器快取
  - HTTP Cache (Cache-Control, ETag)
  - Service Worker Cache
  - IndexedDB

L2: CDN 快取
  - Edge Locations
  - TTL 控制

L3: 應用層快取
  - Redis / Memcached
  - Application Memory Cache

L4: 資料庫查詢快取
  - Query Cache
  - Materialized Views
```

**Redis 快取模式**:

```javascript
// Cache-Aside Pattern (最常用)
async function getUser(userId) {
  const cacheKey = `user:${userId}`;

  // 1. 檢查快取
  let user = await redis.get(cacheKey);

  if (user) {
    return JSON.parse(user);
  }

  // 2. 快取未命中,查詢資料庫
  user = await db.users.findById(userId);

  // 3. 寫入快取
  await redis.setex(cacheKey, 3600, JSON.stringify(user));

  return user;
}

// Write-Through Pattern (寫入時更新快取)
async function updateUser(userId, updates) {
  const cacheKey = `user:${userId}`;

  // 1. 更新資料庫
  const user = await db.users.update(userId, updates);

  // 2. 更新快取
  await redis.setex(cacheKey, 3600, JSON.stringify(user));

  return user;
}

// Write-Behind Pattern (非同步寫入資料庫)
const writeQueue = [];

async function updateUser(userId, updates) {
  const cacheKey = `user:${userId}`;

  // 1. 立即更新快取
  const user = { id: userId, ...updates };
  await redis.setex(cacheKey, 3600, JSON.stringify(user));

  // 2. 加入寫入隊列
  writeQueue.push({ userId, updates });

  return user;
}

// 背景任務定期寫入資料庫
setInterval(async () => {
  const batch = writeQueue.splice(0, 100);

  for (const { userId, updates } of batch) {
    await db.users.update(userId, updates);
  }
}, 5000);
```

### 6.2 快取失效策略

```javascript
// TTL (Time To Live)
await redis.setex('key', 3600, 'value'); // 1 小時後過期

// 主動失效
await redis.del('user:123');

// 標籤失效 (Tag-based Invalidation)
class CacheManager {
  async set(key, value, tags = [], ttl = 3600) {
    await redis.setex(key, ttl, JSON.stringify(value));

    // 為每個標籤建立集合
    for (const tag of tags) {
      await redis.sadd(`tag:${tag}`, key);
      await redis.expire(`tag:${tag}`, ttl);
    }
  }

  async invalidateTag(tag) {
    // 獲取所有相關 keys
    const keys = await redis.smembers(`tag:${tag}`);

    // 刪除所有 keys
    if (keys.length > 0) {
      await redis.del(...keys);
    }

    // 刪除標籤集合
    await redis.del(`tag:${tag}`);
  }
}

// 使用
const cache = new CacheManager();

await cache.set('user:123', userData, ['user', 'user:123']);
await cache.set('user:456', userData, ['user', 'user:456']);

// 清除所有 user 相關快取
await cache.invalidateTag('user');
```

---

## Part 7: 併發與並行優化

### 7.1 限流 (Rate Limiting)

```javascript
// Token Bucket 算法
class TokenBucket {
  constructor(capacity, refillRate) {
    this.capacity = capacity;
    this.tokens = capacity;
    this.refillRate = refillRate; // tokens per second
    this.lastRefill = Date.now();
  }

  refill() {
    const now = Date.now();
    const timePassed = (now - this.lastRefill) / 1000;
    const tokensToAdd = timePassed * this.refillRate;

    this.tokens = Math.min(this.capacity, this.tokens + tokensToAdd);
    this.lastRefill = now;
  }

  tryConsume(tokens = 1) {
    this.refill();

    if (this.tokens >= tokens) {
      this.tokens -= tokens;
      return true;
    }

    return false;
  }
}

// 使用
const limiter = new TokenBucket(100, 10); // 100 容量, 每秒補充 10

app.use((req, res, next) => {
  if (limiter.tryConsume(1)) {
    next();
  } else {
    res.status(429).json({ error: 'Too many requests' });
  }
});

// Redis 實作分散式限流
async function rateLimitRedis(userId, limit, window) {
  const key = `ratelimit:${userId}`;
  const now = Date.now();

  // 使用 Sorted Set
  await redis.zadd(key, now, `${now}-${Math.random()}`);

  // 移除過期記錄
  await redis.zremrangebyscore(key, 0, now - window);

  // 計算請求數
  const count = await redis.zcard(key);

  // 設定過期
  await redis.expire(key, Math.ceil(window / 1000));

  return count <= limit;
}
```

---

## Part 8: 效能監控與可觀測性

### 8.1 Application Performance Monitoring (APM)

```javascript
// 使用 Elastic APM
const apm = require('elastic-apm-node').start({
  serviceName: 'my-app',
  serverUrl: 'http://localhost:8200',
  environment: 'production'
});

const express = require('express');
const app = express();

app.get('/api/users/:id', async (req, res) => {
  // 自訂 Transaction
  const transaction = apm.startTransaction('Get User', 'request');

  try {
    // Span 1: 資料庫查詢
    const span1 = apm.startSpan('DB Query');
    const user = await db.users.findById(req.params.id);
    span1?.end();

    // Span 2: 外部 API 調用
    const span2 = apm.startSpan('External API');
    const enrichedData = await fetchExternalData(user);
    span2?.end();

    transaction?.result = 'success';
    res.json(enrichedData);
  } catch (err) {
    apm.captureError(err);
    transaction?.result = 'error';
    res.status(500).json({ error: err.message });
  } finally {
    transaction?.end();
  }
});
```

### 8.2 SLI/SLO/SLA 定義

```yaml
Service Level Indicators (SLI):

- Availability: 服務可用時間百分比
  SLI = (正常時間 / 總時間) × 100%

- Latency: 請求響應時間
  SLI = P95 延遲 < 200ms 的請求百分比

- Error Rate: 錯誤率
  SLI = (成功請求 / 總請求) × 100%

Service Level Objectives (SLO):

- 可用性目標: 99.9% (允許每月 43 分鐘停機)
- 延遲目標: 95% 的請求 < 200ms
- 錯誤率目標: < 0.1%

Service Level Agreements (SLA):

- 承諾給客戶的服務標準
- 通常低於內部 SLO (留有緩衝)
- 例如: SLA 99.5%, 內部 SLO 99.9%
```

---

## Part 9: 容量規劃與擴展

### 9.1 容量估算

```yaml
容量規劃步驟:

1. 估算流量:
   - 日活躍用戶 (DAU): 1,000,000
   - 每用戶平均請求: 20 次/天
   - 總請求量: 20,000,000 次/天
   - 平均 QPS: 20M / 86400 ≈ 231 QPS
   - 峰值 QPS (3x): ~700 QPS

2. 估算儲存:
   - 每用戶資料大小: 10 KB
   - 1M 用戶: 10 GB
   - 3 年成長 (5x): 50 GB
   - 備份和副本 (3x): 150 GB

3. 估算頻寬:
   - 平均響應大小: 50 KB
   - 峰值流量: 700 QPS × 50 KB = 35 MB/s
   - 需要頻寬: ~300 Mbps

4. 估算服務器數量:
   - 單服務器處理能力: 200 QPS
   - 需要服務器: 700 / 200 = 3.5 → 4 台
   - 冗餘 (2x): 8 台
```

### 9.2 水平擴展 vs 垂直擴展

```yaml
垂直擴展 (Scale Up):

優勢:
  ✅ 簡單 (不需修改架構)
  ✅ 無分散式複雜性

劣勢:
  ❌ 有硬體上限
  ❌ 單點故障風險
  ❌ 成本增長非線性

適用場景:
  - 初期小規模系統
  - 資料庫伺服器
  - 快速解決效能問題

水平擴展 (Scale Out):

優勢:
  ✅ 無理論上限
  ✅ 高可用性
  ✅ 成本線性增長

劣勢:
  ❌ 架構複雜
  ❌ 需要負載均衡
  ❌ 資料一致性挑戰

適用場景:
  - 大規模系統
  - 無狀態服務
  - 微服務架構
```

---

## Part 10: 真實案例研究

### Case Study: 電商平台雙11效能優化

**背景**:
- 平時日均 100 萬訂單
- 雙11 峰值預計 1000 萬訂單/天
- 峰值 QPS 可達 50,000
- 系統需要支撐 10 倍流量

**優化措施**:

```yaml
Phase 1: 前端優化 (1 個月前)
  ✅ 靜態資源全部遷移到 CDN
  ✅ 圖片使用 WebP 格式,減少 60% 大小
  ✅ 實施 Code Splitting,首屏載入時間從 3s 降至 800ms
  ✅ 使用 Service Worker 預快取關鍵資源

Phase 2: 後端優化 (2 週前)
  ✅ 資料庫查詢優化,添加 50+ 索引
  ✅ 引入 Redis Cluster (6 節點)
  ✅ 訂單寫入改為非同步 (使用 Kafka)
  ✅ 熱點商品數據預載入記憶體

Phase 3: 架構調整 (1 週前)
  ✅ 服務器從 20 台擴展到 100 台
  ✅ 資料庫主從分離 (1 主 5 從)
  ✅ 實施讀寫分離
  ✅ 分庫分表 (按用戶 ID hash)

Phase 4: 限流降級 (活動當天)
  ✅ 實施分級限流:
    - API Gateway: 50,000 QPS
    - 單用戶: 10 req/min
    - 支付服務: 20,000 TPS
  ✅ 降級策略:
    - 關閉推薦系統
    - 簡化商品詳情頁
    - 延遲發送通知郵件

成果:
  - 峰值 QPS: 45,000 (成功支撐)
  - P99 延遲: 從 3s 降至 500ms
  - 系統可用性: 99.95%
  - 訂單成功率: 99.8%
```

---

## 總結

本深度技術指南涵蓋了效能優化的進階主題:

✅ **效能分析方法論** - USE, RED, Flamegraph
✅ **前端效能優化** - CRP, JavaScript, 資源載入
✅ **後端效能優化** - 非同步處理, 連接池
✅ **資料庫調優** - 索引優化, 查詢優化
✅ **網路層優化** - HTTP/2, CDN策略
✅ **快取策略** - 多層快取, 失效策略
✅ **併發優化** - 限流, 並行處理
✅ **效能監控** - APM, SLI/SLO/SLA
✅ **容量規劃** - 估算, 擴展策略
✅ **真實案例** - 電商平台雙11優化

---

## 📚 參考資源

- [Performance SOP 完整版](./SOP.md)
- [Performance QuickRef 快速參考](./SOP_QuickRef.md)
- [Performance 快速啟動指令集](../../prompts/scenario-prompts/performance-prompts.md)
- [performance-optimization-flow Workflow](../../workflow/scenario-specific/performance-optimization-flow.md)
- [AISDLC_INIT.md](../../AISDLC_INIT.md)

### 相關 Agents
- [performance-engineer-zh.yaml](../../agent/specialized/performance-engineer-zh.yaml) - Performance Engineer（主導）
- [sd-architect-zh.yaml](../../agent/core/05.sd-architect-zh.yaml) - Marcus（架構優化）
- [dev-senior-zh.yaml](../../agent/specialized/dev-senior-zh.yaml) - Senior Developer（代碼優化）
- [qa-automation-zh.yaml](../../agent/specialized/qa-automation-zh.yaml) - QA Automation（效能測試）
- [devops-engineer-zh.yaml](../../agent/specialized/devops-engineer-zh.yaml) - DevOps Engineer（基礎設施與監控）
- [code-analyzer-zh.yaml](../../agent/specialized/code-analyzer-zh.yaml) - CodeX（代碼效能分析，選用）
- [security-engineer-zh.yaml](../../agent/specialized/security-engineer-zh.yaml) - Security Engineer（安全敏感區域優化，選用）
- [sd-mobile-architect-zh.yaml](../../agent/specialized/sd-mobile-architect-zh.yaml) - Mobile Architect（行動端架構優化，選用）
- [qa-mobile-tester-zh.yaml](../../agent/specialized/qa-mobile-tester-zh.yaml) - Mobile QA（行動端效能測試，選用）

---

**文檔版本: v0.01
**最後更新**: 2026-02-17
**維護者**: AISDLC Framework Team
