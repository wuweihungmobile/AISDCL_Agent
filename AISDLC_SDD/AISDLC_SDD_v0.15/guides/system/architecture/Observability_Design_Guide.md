# 可觀測性設計指南
# Observability Design Guide

**文件版本**: v1.0
**建立日期**: 2025-11-20
**適用範圍**: AISDLC-SDD v0.01+
**文件類型**: 架構設計指南

---

## 📋 文件概述

### 目的

本指南定義應用程式的可觀測性 (Observability) 設計標準，包含日誌 (Logging)、指標 (Metrics) 和追蹤 (Tracing) 三大支柱，確保系統在生產環境中可被監控、除錯和優化。

### 適用場景

- ✅ 所有 Greenfield 專案（Stage 5 架構設計階段）
- ✅ Brownfield 專案的可觀測性改進
- ✅ DevOps 專案的監控設置
- ✅ 生產環境問題排查準備

### 可觀測性三大支柱

```
┌─────────────────────────────────────────────────────┐
│              Observability 三大支柱                  │
├─────────────────────────────────────────────────────┤
│                                                      │
│  🪵 Logging          📊 Metrics         🔍 Tracing  │
│  (事件記錄)          (指標監控)         (分散式追蹤) │
│                                                      │
│  • 錯誤日誌          • CPU/Memory       • Request ID │
│  • 審計日誌          • Request Rate     • Span       │
│  • 業務日誌          • Error Rate       • 呼叫鏈     │
│  • 除錯日誌          • Latency P95      • 瓶頸分析   │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

## 🪵 日誌設計 (Logging)

### 1. 日誌層級定義

| 層級 | 用途 | 使用時機 | 生產環境 |
|-----|------|---------|---------|
| **ERROR** | 錯誤事件 | 異常、失敗、需要立即處理 | ✅ 啟用 |
| **WARN** | 警告事件 | 潛在問題、降級服務 | ✅ 啟用 |
| **INFO** | 資訊事件 | 重要業務流程、狀態變更 | ✅ 啟用 |
| **DEBUG** | 除錯資訊 | 詳細執行流程、變數狀態 | ❌ 停用 |
| **TRACE** | 追蹤資訊 | 最詳細的執行路徑 | ❌ 停用 |

**生產環境建議**: `INFO` 或 `WARN` 以上

---

### 2. 結構化日誌格式 (Structured Logging)

**✅ 推薦：JSON 格式**

```json
{
  "timestamp": "2025-11-20T10:30:45.123Z",
  "level": "ERROR",
  "service": "order-service",
  "environment": "production",
  "version": "v1.2.3",
  "traceId": "abc123-def456-ghi789",
  "spanId": "span-001",
  "userId": "user_12345",
  "sessionId": "session_67890",
  "requestId": "req_xyz789",
  "ip": "192.168.1.100",
  "userAgent": "Mozilla/5.0...",
  "method": "POST",
  "path": "/api/orders",
  "statusCode": 500,
  "duration": 1234,
  "error": {
    "message": "Database connection failed",
    "stack": "Error: Connection timeout...",
    "code": "DB_CONN_TIMEOUT"
  },
  "metadata": {
    "orderId": "ORD-12345",
    "amount": 99.99,
    "currency": "USD"
  }
}
```

**❌ 避免：非結構化日誌**

```
2025-11-20 10:30:45 ERROR Database connection failed for order ORD-12345
```

**原因**:
- 難以解析和查詢
- 無法聚合分析
- 無法建立告警規則

---

### 3. 必須記錄的日誌類型

#### 3.1 應用程式日誌 (Application Logs)

**ERROR 層級**:
- [x] **未捕獲的異常** (Uncaught Exceptions)
  ```javascript
  // Node.js Example
  process.on('uncaughtException', (error) => {
    logger.error('Uncaught Exception', { error: error.message, stack: error.stack });
    process.exit(1);
  });
  ```

- [x] **API 請求失敗** (5xx Errors)
  ```javascript
  app.use((err, req, res, next) => {
    logger.error('API Request Failed', {
      method: req.method,
      path: req.path,
      statusCode: 500,
      error: err.message,
      stack: err.stack,
      requestId: req.id
    });
    res.status(500).json({ error: 'Internal Server Error' });
  });
  ```

- [x] **資料庫操作失敗**
  ```javascript
  try {
    await db.query('SELECT * FROM users WHERE id = ?', [userId]);
  } catch (error) {
    logger.error('Database Query Failed', {
      query: 'SELECT users',
      userId,
      error: error.message,
      code: error.code
    });
    throw error;
  }
  ```

- [x] **第三方服務呼叫失敗**
  ```javascript
  try {
    const response = await stripe.charges.create({ amount: 1000 });
  } catch (error) {
    logger.error('Stripe API Failed', {
      service: 'stripe',
      operation: 'charges.create',
      error: error.message,
      statusCode: error.statusCode
    });
    throw error;
  }
  ```

**WARN 層級**:
- [x] **降級服務啟用** (Circuit Breaker Open)
- [x] **Retry 機制觸發**
- [x] **快取失效或過期**
- [x] **Rate Limit 接近閾值**
- [x] **資源使用率高於 80%**

**INFO 層級**:
- [x] **應用程式啟動/關閉**
  ```javascript
  logger.info('Application Started', {
    service: 'order-service',
    version: '1.2.3',
    environment: 'production',
    port: 3000
  });
  ```

- [x] **重要業務操作**
  - 用戶註冊/登入
  - 訂單建立/完成
  - 支付成功/失敗
  - 權限變更

- [x] **排程任務執行**
  ```javascript
  cron.schedule('0 2 * * *', () => {
    logger.info('Daily Backup Job Started');
    // 執行備份
    logger.info('Daily Backup Job Completed', { duration: 12345 });
  });
  ```

#### 3.2 安全審計日誌 (Security Audit Logs)

**必須記錄**:
- [x] **身份認證事件**
  - 登入成功/失敗
  - 登出
  - 密碼重設
  - MFA 驗證

- [x] **權限變更**
  - 用戶角色變更
  - 權限授予/撤銷
  - API Key 建立/刪除

- [x] **敏感操作**
  - 個資存取/修改/刪除
  - 財務交易
  - 管理員操作

**範例**:
```javascript
logger.info('User Login Success', {
  eventType: 'AUTH',
  action: 'LOGIN_SUCCESS',
  userId: 'user_12345',
  ip: '192.168.1.100',
  userAgent: req.headers['user-agent'],
  mfaUsed: true,
  loginMethod: 'password'
});

logger.warn('User Login Failed', {
  eventType: 'AUTH',
  action: 'LOGIN_FAILED',
  email: 'user@example.com', // 不記錄密碼！
  ip: '192.168.1.100',
  reason: 'invalid_password',
  attemptCount: 3
});
```

#### 3.3 效能日誌 (Performance Logs)

- [x] **慢查詢 (Slow Queries > 1s)**
  ```javascript
  const startTime = Date.now();
  const result = await db.query('SELECT ...');
  const duration = Date.now() - startTime;

  if (duration > 1000) {
    logger.warn('Slow Query Detected', {
      query: 'SELECT users JOIN orders',
      duration,
      threshold: 1000
    });
  }
  ```

- [x] **HTTP 請求超時**
- [x] **記憶體使用異常**
- [x] **GC (Garbage Collection) 事件**

---

### 4. 日誌內容規範

#### 4.1 ✅ 應該記錄

- [x] Timestamp (ISO 8601 格式)
- [x] Log Level (ERROR/WARN/INFO)
- [x] Service Name
- [x] Environment (production/staging/dev)
- [x] Trace ID / Request ID (分散式追蹤)
- [x] User ID / Session ID
- [x] IP Address
- [x] HTTP Method / Path
- [x] Status Code
- [x] Duration (ms)
- [x] Error Message / Stack Trace
- [x] 業務相關 Metadata

#### 4.2 ❌ 不應記錄 (敏感資訊)

- [ ] **密碼** (Password)
- [ ] **API Keys / Secrets**
- [ ] **信用卡號** (PAN - Primary Account Number)
- [ ] **CVV / CVC**
- [ ] **完整個人資料** (身分證號、護照號)
- [ ] **JWT Token 完整內容**
- [ ] **Session Token**

**範例：敏感資訊遮罩**

```javascript
// ❌ 錯誤
logger.info('User login attempt', {
  email: 'user@example.com',
  password: 'MyPassword123!' // 不應記錄！
});

// ✅ 正確
logger.info('User login attempt', {
  email: 'user@example.com',
  // password 不記錄
});

// ✅ 正確：遮罩信用卡號
logger.info('Payment processed', {
  cardNumber: '****-****-****-1234', // 僅顯示後4碼
  amount: 99.99
});

// ✅ 正確：遮罩 Email
logger.info('Email sent', {
  email: 'u***@example.com' // 部分遮罩
});
```

---

### 5. 日誌庫選擇

| 語言/框架 | 推薦日誌庫 | 特色 |
|----------|-----------|------|
| **Node.js** | Winston, Pino | 結構化日誌、高效能 |
| **Python** | structlog, loguru | 結構化日誌、易用 |
| **Java** | Logback, Log4j2 | 企業級、高度可配置 |
| **Go** | zap, zerolog | 高效能、零記憶體分配 |
| **Ruby** | semantic_logger | 結構化日誌 |
| **.NET** | Serilog | 結構化日誌、Sink 豐富 |

**Node.js 範例 (Pino)**:

```javascript
const pino = require('pino');

const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  formatters: {
    level: (label) => {
      return { level: label.toUpperCase() };
    },
  },
  timestamp: pino.stdTimeFunctions.isoTime,
});

// 使用
logger.info({ userId: '123', action: 'login' }, 'User logged in');
```

---

### 6. 日誌存儲與管理

#### 6.1 日誌保留期限

| 日誌類型 | 保留期限 | 備註 |
|---------|---------|------|
| **應用程式日誌** | 30 天 | Hot Storage (ELK/Loki) |
| **安全審計日誌** | 1 年+ | Cold Storage (S3/GCS) |
| **效能日誌** | 30 天 | - |
| **除錯日誌** | 7 天 | 僅 Staging 環境 |

#### 6.2 日誌存儲方案

| 方案 | 適用場景 | 成本 | 查詢效能 |
|-----|---------|-----|---------|
| **ELK Stack** (Elasticsearch, Logstash, Kibana) | 自建、完整功能 | 中 | 高 |
| **Loki + Grafana** | 輕量級、K8s 友善 | 低 | 中 |
| **CloudWatch Logs** (AWS) | AWS 原生整合 | 中 | 中 |
| **Google Cloud Logging** (GCP) | GCP 原生整合 | 中 | 高 |
| **DataDog / New Relic** | 商業 SaaS、功能完整 | 高 | 高 |
| **Splunk** | 企業級 | 高 | 高 |

#### 6.3 日誌輪轉 (Log Rotation)

**檔案系統日誌** (非雲端環境):

```javascript
// Winston 範例
const winston = require('winston');
require('winston-daily-rotate-file');

const logger = winston.createLogger({
  transports: [
    new winston.transports.DailyRotateFile({
      filename: 'logs/application-%DATE%.log',
      datePattern: 'YYYY-MM-DD',
      maxSize: '100m', // 單檔最大 100MB
      maxFiles: '30d', // 保留 30 天
      zippedArchive: true // 自動壓縮
    })
  ]
});
```

---

## 📊 指標監控 (Metrics)

### 1. 核心指標分類

#### 1.1 四大黃金信號 (Four Golden Signals)

| 信號 | 定義 | 指標範例 | 告警閾值 |
|-----|------|---------|---------|
| **Latency** | 請求回應時間 | P50, P95, P99 | P95 > 500ms |
| **Traffic** | 請求流量 | RPS (Requests Per Second) | - |
| **Errors** | 錯誤率 | HTTP 5xx Error Rate | > 1% |
| **Saturation** | 資源飽和度 | CPU, Memory, Disk 使用率 | > 80% |

#### 1.2 應用程式指標 (Application Metrics)

**HTTP 指標**:
- [x] `http_requests_total` - 總請求數 (Counter)
- [x] `http_request_duration_seconds` - 請求時長 (Histogram)
- [x] `http_requests_in_flight` - 進行中的請求 (Gauge)
- [x] `http_response_size_bytes` - 回應大小 (Summary)

**資料庫指標**:
- [x] `db_query_duration_seconds` - 查詢時長
- [x] `db_connections_active` - 活躍連線數
- [x] `db_connections_idle` - 閒置連線數
- [x] `db_connection_errors_total` - 連線錯誤數

**業務指標**:
- [x] `orders_created_total` - 訂單建立數
- [x] `payments_successful_total` - 成功支付數
- [x] `user_registrations_total` - 用戶註冊數
- [x] `revenue_total` - 總收入 (Gauge)

#### 1.3 基礎設施指標 (Infrastructure Metrics)

- [x] **CPU 使用率** (`node_cpu_usage_percent`)
- [x] **記憶體使用率** (`node_memory_usage_percent`)
- [x] **磁碟 I/O** (`node_disk_io_bytes`)
- [x] **網路流量** (`node_network_transmit_bytes`)
- [x] **檔案描述符** (`node_open_file_descriptors`)

---

### 2. 指標類型

| 類型 | 說明 | 使用場景 | 範例 |
|-----|------|---------|------|
| **Counter** | 只增不減的計數器 | 累積值 | 總請求數、錯誤數 |
| **Gauge** | 可增可減的數值 | 瞬時值 | CPU 使用率、記憶體 |
| **Histogram** | 分布統計 | 時長、大小分布 | 請求時長 P95/P99 |
| **Summary** | 分位數統計 | 百分位數 | 回應時間分位數 |

---

### 3. Prometheus 指標範例

**Node.js (prom-client)**:

```javascript
const promClient = require('prom-client');

// 註冊預設指標 (CPU, Memory, etc.)
promClient.collectDefaultMetrics();

// Counter: 總請求數
const httpRequestsTotal = new promClient.Counter({
  name: 'http_requests_total',
  help: 'Total HTTP requests',
  labelNames: ['method', 'path', 'status']
});

// Histogram: 請求時長
const httpRequestDuration = new promClient.Histogram({
  name: 'http_request_duration_seconds',
  help: 'HTTP request duration',
  labelNames: ['method', 'path'],
  buckets: [0.1, 0.5, 1, 2, 5] // 秒
});

// Gauge: 進行中的請求
const httpRequestsInFlight = new promClient.Gauge({
  name: 'http_requests_in_flight',
  help: 'Current HTTP requests in flight',
  labelNames: ['method']
});

// Express Middleware
app.use((req, res, next) => {
  const end = httpRequestDuration.startTimer();
  httpRequestsInFlight.inc({ method: req.method });

  res.on('finish', () => {
    httpRequestsTotal.inc({
      method: req.method,
      path: req.route?.path || req.path,
      status: res.statusCode
    });
    end({ method: req.method, path: req.route?.path || req.path });
    httpRequestsInFlight.dec({ method: req.method });
  });

  next();
});

// Metrics Endpoint
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', promClient.register.contentType);
  res.end(await promClient.register.metrics());
});
```

---

### 4. 告警規則設計

**Prometheus Alert Rules**:

```yaml
# alerts.yml
groups:
  - name: application_alerts
    interval: 30s
    rules:
      # 高錯誤率告警
      - alert: HighErrorRate
        expr: |
          (
            sum(rate(http_requests_total{status=~"5.."}[5m]))
            /
            sum(rate(http_requests_total[5m]))
          ) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"

      # 高延遲告警
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95,
            rate(http_request_duration_seconds_bucket[5m])
          ) > 0.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "P95 latency is high"
          description: "P95 latency is {{ $value }}s"

      # 高 CPU 使用率
      - alert: HighCPUUsage
        expr: node_cpu_usage_percent > 80
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "CPU usage is high"
          description: "CPU usage is {{ $value }}%"

      # 記憶體不足
      - alert: LowMemory
        expr: node_memory_available_bytes < 1073741824 # < 1GB
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Low memory available"
          description: "Available memory is {{ $value | humanize }}B"
```

---

## 🔍 分散式追蹤 (Distributed Tracing)

### 1. 追蹤概念

```
Client Request
    │
    ├─ Span 1: API Gateway (100ms)
    │   │
    │   ├─ Span 2: Auth Service (20ms)
    │   │
    │   ├─ Span 3: Order Service (60ms)
    │   │   │
    │   │   ├─ Span 4: Database Query (30ms)
    │   │   │
    │   │   └─ Span 5: Payment Service (20ms)
    │   │       │
    │   │       └─ Span 6: Stripe API (15ms)
    │   │
    │   └─ Span 7: Notification Service (10ms)
    │
    └─ Total: 100ms
```

**關鍵概念**:
- **Trace**: 一個完整的請求路徑
- **Span**: Trace 中的一個操作單元
- **Trace ID**: 唯一識別一個 Trace
- **Span ID**: 唯一識別一個 Span
- **Parent Span ID**: 父 Span 的 ID

---

### 2. OpenTelemetry 實作

**Node.js 範例**:

```javascript
const { NodeTracerProvider } = require('@opentelemetry/sdk-trace-node');
const { JaegerExporter } = require('@opentelemetry/exporter-jaeger');
const { registerInstrumentations } = require('@opentelemetry/instrumentation');
const { HttpInstrumentation } = require('@opentelemetry/instrumentation-http');
const { ExpressInstrumentation } = require('@opentelemetry/instrumentation-express');

// 初始化 Tracer
const provider = new NodeTracerProvider();

// Jaeger Exporter
const exporter = new JaegerExporter({
  endpoint: 'http://localhost:14268/api/traces',
  serviceName: 'order-service',
});

provider.addSpanProcessor(new BatchSpanProcessor(exporter));
provider.register();

// 自動 Instrumentation
registerInstrumentations({
  instrumentations: [
    new HttpInstrumentation(),
    new ExpressInstrumentation(),
  ],
});

// 手動 Span
const tracer = trace.getTracer('order-service');

async function createOrder(orderId) {
  const span = tracer.startSpan('createOrder');
  span.setAttribute('order.id', orderId);

  try {
    // 業務邏輯
    await saveToDatabase(orderId);
    span.setStatus({ code: SpanStatusCode.OK });
  } catch (error) {
    span.setStatus({
      code: SpanStatusCode.ERROR,
      message: error.message
    });
    throw error;
  } finally {
    span.end();
  }
}
```

---

### 3. Trace Context 傳遞

**HTTP Headers**:

```
traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01
  │   │                                    │                │
  │   └─ Trace ID                          └─ Span ID       └─ Flags
  └─ Version
```

**實作範例**:

```javascript
// 發送請求時注入 Trace Context
const axios = require('axios');
const { propagation, context } = require('@opentelemetry/api');

async function callExternalService() {
  const headers = {};
  propagation.inject(context.active(), headers);

  const response = await axios.get('https://api.example.com/data', {
    headers: headers // 自動包含 traceparent
  });

  return response.data;
}
```

---

## 🛠️ 技術棧選擇

### 1. 完整可觀測性方案

#### 方案 A: ELK + Prometheus + Jaeger (自建)

```
┌─────────────────────────────────────────────┐
│              Application                     │
├─────────────────────────────────────────────┤
│  Logs ─────► Filebeat ─────► Logstash ─────► Elasticsearch ─────► Kibana   │
│  Metrics ──► Prometheus ───► Grafana        │
│  Traces ───► Jaeger Collector ─────► Jaeger UI │
└─────────────────────────────────────────────┘
```

**優點**:
- ✅ 完全開源、免費
- ✅ 高度可客製化
- ✅ 社群支援強

**缺點**:
- ❌ 維護成本高
- ❌ 需要專業運維

---

#### 方案 B: Grafana Stack (Loki + Tempo + Prometheus)

```
┌─────────────────────────────────────────────┐
│              Application                     │
├─────────────────────────────────────────────┤
│  Logs ─────► Loki                           │
│  Metrics ──► Prometheus                     │
│  Traces ───► Tempo                          │
│              └─────► Grafana (統一視覺化)   │
└─────────────────────────────────────────────┘
```

**優點**:
- ✅ 統一 UI (Grafana)
- ✅ 輕量級、低成本
- ✅ 與 Kubernetes 整合良好

---

#### 方案 C: 雲端原生方案

**AWS**:
- Logs: CloudWatch Logs
- Metrics: CloudWatch Metrics
- Traces: X-Ray

**GCP**:
- Logs: Cloud Logging
- Metrics: Cloud Monitoring
- Traces: Cloud Trace

**Azure**:
- Logs: Azure Monitor Logs
- Metrics: Azure Monitor Metrics
- Traces: Application Insights

**優點**:
- ✅ 零維護
- ✅ 與雲端服務深度整合

**缺點**:
- ❌ Vendor Lock-in
- ❌ 成本較高

---

#### 方案 D: 商業 SaaS (DataDog / New Relic / Dynatrace)

**優點**:
- ✅ 功能最完整
- ✅ UI/UX 最佳
- ✅ AI 驅動的異常檢測

**缺點**:
- ❌ 成本最高
- ❌ 資料存儲在第三方

---

### 2. 技術棧選擇決策樹

```
是否有專職 DevOps 團隊？
    │
    ├─ 是 ──► 考慮自建方案 (ELK / Grafana Stack)
    │
    └─ 否 ──► 考慮雲端原生 or SaaS
               │
               ├─ 預算充足？
               │   ├─ 是 ──► DataDog / New Relic
               │   └─ 否 ──► 雲端原生方案
               │
               └─ 使用 Kubernetes？
                   ├─ 是 ──► Grafana Stack (Loki + Tempo)
                   └─ 否 ──► 雲端原生方案
```

---

## ✅ 實作檢查清單

### Stage 5: 架構設計階段

- [ ] **日誌設計**
  - [ ] 選擇日誌庫 (Winston/Pino/Logback)
  - [ ] 定義日誌層級 (INFO 以上)
  - [ ] 設計結構化日誌格式 (JSON)
  - [ ] 定義必須記錄的事件類型
  - [ ] 定義敏感資訊遮罩規則
  - [ ] 設計日誌儲存方案 (ELK/Loki/CloudWatch)
  - [ ] 設計日誌保留期限 (30天/1年)

- [ ] **指標監控**
  - [ ] 定義核心指標 (四大黃金信號)
  - [ ] 定義業務指標 (訂單數、收入)
  - [ ] 選擇指標收集方案 (Prometheus/CloudWatch)
  - [ ] 設計告警規則與閾值
  - [ ] 設計 Dashboard (Grafana)

- [ ] **分散式追蹤**
  - [ ] 選擇追蹤方案 (Jaeger/Tempo/X-Ray)
  - [ ] 整合 OpenTelemetry SDK
  - [ ] 定義自動 Instrumentation 範圍
  - [ ] 定義需要手動 Span 的關鍵路徑
  - [ ] 設計 Trace Context 傳遞機制

- [ ] **告警與通知**
  - [ ] 定義告警等級 (Critical/Warning/Info)
  - [ ] 定義通知渠道 (Email/Slack/PagerDuty)
  - [ ] 設計 On-call 輪值機制
  - [ ] 設計告警升級流程

- [ ] **文檔產出**
  - [ ] 可觀測性設計文件 (本指南)
  - [ ] 日誌規範文件
  - [ ] 告警 Runbook
  - [ ] Dashboard 清單

---

### Stage 8: 開發準備階段

- [ ] **環境設置**
  - [ ] 安裝日誌庫依賴
  - [ ] 配置 Prometheus Exporter
  - [ ] 整合 OpenTelemetry SDK
  - [ ] 配置日誌儲存 (ELK/Loki)
  - [ ] 配置 Grafana Dashboards

- [ ] **程式碼整合**
  - [ ] 實作結構化日誌
  - [ ] 實作 HTTP Middleware (日誌、指標)
  - [ ] 實作資料庫查詢 Instrumentation
  - [ ] 實作第三方 API 呼叫追蹤
  - [ ] 實作業務指標收集

- [ ] **測試驗證**
  - [ ] 驗證日誌正確輸出
  - [ ] 驗證 `/metrics` 端點
  - [ ] 驗證 Trace 完整性
  - [ ] 驗證告警規則觸發
  - [ ] 壓力測試監控表現

---

## 📚 最佳實踐

### 1. 日誌最佳實踐

- ✅ **使用結構化日誌** (JSON)，不要用純文字
- ✅ **包含 Trace ID / Request ID**，方便追蹤
- ✅ **遮罩敏感資訊**，不要記錄密碼、信用卡號
- ✅ **使用適當的日誌層級**，生產環境用 INFO 以上
- ✅ **非同步寫入日誌**，避免阻塞主執行緒
- ✅ **設定日誌輪轉**，避免磁碟空間耗盡
- ❌ 不要在迴圈中大量記錄日誌（效能問題）
- ❌ 不要記錄過大的物件（JSON.stringify 整個 Request）

### 2. 指標最佳實踐

- ✅ **使用標準命名規範** (`http_requests_total`)
- ✅ **Label 使用低基數值**（不要用 User ID 當 Label）
- ✅ **選擇正確的指標類型** (Counter/Gauge/Histogram)
- ✅ **記錄業務指標**，不只是技術指標
- ❌ 不要建立過多指標（< 1000 個）
- ❌ 不要使用高基數 Label (如 Email, IP)

### 3. 追蹤最佳實踐

- ✅ **自動 Instrumentation 優先**，減少手動程式碼
- ✅ **在關鍵路徑加入自訂 Span**
- ✅ **傳遞 Trace Context** 到所有下游服務
- ✅ **取樣策略** (Sampling)，避免儲存所有 Trace
- ❌ 不要在 Span 中記錄敏感資訊

---

## 📞 延伸閱讀

- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Google SRE Book - Monitoring](https://sre.google/sre-book/monitoring-distributed-systems/)
- [The Twelve-Factor App - Logs](https://12factor.net/logs)
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)

---

**文件版本歷史**:

| 版本 | 日期 | 變更內容 | 作者 |
|-----|------|---------|------|
| v1.0 | 2025-11-20 | 初始版本 | Claude |
