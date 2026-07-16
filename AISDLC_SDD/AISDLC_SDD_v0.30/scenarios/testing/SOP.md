# Testing Strategy & Automation 測試策略與自動化 SOP

**版本**: v0.01 | **最後更新**: 2026-02-12
> 📝 **關於範例連結說明**:
> 本 SOP 中部分連結（如測試計畫文檔、測試案例清單、測試報告模板等路徑）為示例性質，
> 展示一般專案的測試文檔結構。實際使用時，請根據您的專案測試策略和文檔組織調整路徑。

## 🎯 情境概述

**適用場景**：測試策略制定、測試金字塔建立、自動化測試實作、測試環境管理

**預計時間**:
- 📋 **AISDLC 規劃階段**: 3-4 小時
  - **規劃時間** (AI 分析 + 人工確認): 3-4 小時
  - **執行時間** (依專案規模):
    - 小型專案 (基本測試覆蓋): 1-2 週
    - 中型專案 (完整測試金字塔): 2-4 週
    - 大型專案 (企業級測試體系): 4-8 週
- 🔨 **實際執行階段**: 1-8 週 (依專案規模而定)

> 💡 **時間估算說明**:
> - **規劃時間**指使用 AISDLC 流程進行測試策略、測試金字塔設計、自動化方案文檔產出的時間
> - **執行時間**指實際測試撰寫和執行的時間，會因測試覆蓋率目標、專案複雜度而有很大差異
> - 時間估算包含人工確認和 AI 輔助分析的完整流程

**涉及角色**：QA-Lead, QA-Automation, Dev, SD

**最終產出**：測試策略文件 + 測試金字塔設計 + 測試案例清單 + 自動化腳本 + 測試環境配置 + 測試報告模板

---

## 🤝 協作模式 (Phase 2: v0.03)

### 主要協作模式

#### 1. Parallel-Convergence (並行收斂)
- **主導 Agent**: QA-Lead (Coordinator)
- **並行 Agents**: QA-Automation (自動化), QA-Tester (手動), QA-Mobile (行動端)
- **使用階段**: 測試執行階段
- **模式說明**: 多測試人員並行測試不同層級和模組

#### 2. Parallel-Convergence 測試結構
```
QA-Lead 分配測試任務
    ↓
┌─────────────┬──────────────┬───────────┐
│ qa-auto     │ qa-tester    │ qa-mobile │
│ (自動化)     │ (手動測試)    │ (行動端)   │
│ Unit/API    │ Exploratory  │ Native    │
└─────────────┴──────────────┴───────────┘
    ↓
QA-Lead 整合測試報告
    ↓
🔴 人類確認
```

### 次要協作模式

#### 3. Lead-Support (主導-支援)
- **使用階段**: 測試策略設計
- **模式說明**: QA-Lead 主導策略，其他 QA 提供專業輸入

### 🔔 Event-Driven Agent Notification（🔴 強制）

> PR 事件通知為強制，部署通知為選配。測試結果自動匯聚至 PR Comment。

📖 **配置範本**: [Event_Driven_Agent_Notification_Template.md](../../docs_template/scenario_specific/devops/Event_Driven_Agent_Notification_Template.md)
🔧 **建置流程**: [devops-setup-flow 步驟 0.10](../../workflow/scenario-specific/devops-setup-flow.md)

---

## 🔗 Skills 整合對照表

> 💡 **說明**: 以下列出各階段可觸發的 Claude Code Skills（斜線指令），協助加速測試規劃與實施。

| SOP 階段 | 可觸發 Skill | 用途說明 |
|---------|-------------|---------|
| 階段 1：測試策略 | `/testing-strategy` | 測試金字塔設計、工具選擇 |
| 階段 2：測試案例 | `/qa-testing` | 測試計畫、驗收測試設計 |
| 階段 2：安全測試 | `/security-audit` | OWASP Top 10 安全測試設計 |
| 階段 2：效能測試 | `/performance-optimization` | 效能基準測試、負載測試設計 |
| 階段 3：自動化 CI | `/devops-github-actions`、`/devops-gitlab-ci` | CI Pipeline 測試整合 |
| 階段 4：測試環境 | `/devops-docker` | Docker Compose 測試環境建置 |
| 階段 5：報告 | `/devops-monitoring` | 測試指標監控與儀表板 |
| 行動端測試 | `/mobile-development` | Android/iOS/macOS 測試框架與裝置矩陣 |
| 程式碼品質 | `/code-review`、`/dev-review` | 程式碼審查與測試品質確保 |
| 資料庫測試 | `/integration-database` | PostgreSQL 測試資料管理 |
| 合規測試 | `/compliance-audit` | 電商 PCI-DSS、付費內容保護、GDPR 合規測試設計（含 PAID/PRICE/RACE 強制測試項）|

---

## 📋 前置準備檢查清單

### 必要材料
- [ ] 專案需求文檔 (PRD/FRD/SRD)
- [ ] 系統架構文檔
- [ ] User Stories 和 Acceptance Criteria
- [ ] 代碼庫存取權限
- [ ] 測試環境存取權限

### 選擇性材料
- [ ] 現有測試案例
- [ ] 已知 Bug 清單
- [ ] 效能需求 (SLA)
- [ ] 合規要求 (GDPR, WCAG)
- [ ] 測試工具偏好
- [ ] **目標平台識別** (Web / Android / iOS / macOS / 跨平台) — 影響測試框架選擇與裝置矩陣

---

## 🔧 材料缺失應對方案

> 💡 **現實情況**: 測試專案常因缺乏完整需求文檔或測試環境而受阻。以下提供實用的替代方案。

| 缺失材料 | 影響程度 | 應對方案 | 預計額外時間 |
|---------|---------|---------|-------------|
| **測試需求 (PRD/FRD/SRD)** | 🔴 高 | • **方案 1**: 與 PM/開發團隊進行需求訪談,逆向推導測試需求<br>• **方案 2**: 分析現有代碼和 API,推測預期行為<br>• **方案 3**: 進行探索性測試,記錄實際行為作為基準<br>• **方案 4**: 使用 SA Agent 協助結構化需求提取 | +2-4 小時 |
| **測試環境** | 🔴 高 | • **方案 1**: 使用 Docker Compose 快速搭建本地測試環境<br>• **方案 2**: 申請雲端測試環境 (AWS/GCP 免費試用)<br>• **方案 3**: 暫時使用開發環境 (需謹慎隔離)<br>• **方案 4**: 使用 Mock/Stub 替代外部依賴 | +2-6 小時 |
| **測試資料** | 🔴 高 | • **方案 1**: 使用 Faker.js 或 Factory Bot 生成測試資料<br>• **方案 2**: 從生產環境匯出並匿名化資料<br>• **方案 3**: 手動建立最小測試資料集<br>• **方案 4**: 使用 Seed Scripts 快速填充資料 | +1-3 小時 |
| **CI/CD 配置** | 🟡 中 | • **方案 1**: 使用 GitHub Actions 免費方案快速配置<br>• **方案 2**: 參考同類專案的 CI/CD 配置模板<br>• **方案 3**: 先本地執行測試,後續再整合 CI/CD<br>• **方案 4**: 使用 DevOps-Engineer Agent 協助生成配置 | +1-2 小時 |
| **Acceptance Criteria (AC)** | 🟡 中 | • **方案 1**: 與 PO/PM 確認驗收標準<br>• **方案 2**: 參考 User Stories 推導 AC<br>• **方案 3**: 使用 Given-When-Then 格式自行定義<br>• **方案 4**: 先測試 Happy Path,後續補充邊界條件 | +0.5-1 小時 |
| **已知 Bug 清單** | 🟢 低 | • **方案 1**: 檢查 Issue Tracker (Jira、GitHub Issues)<br>• **方案 2**: 詢問開發團隊已知問題<br>• **方案 3**: 暫時跳過,聚焦新功能測試<br>• **方案 4**: 執行 Smoke Test 快速發現明顯問題 | +0.5-1 小時 |
| **效能需求 (SLA)** | 🟢 低 | • **方案 1**: 與產品/業務團隊確認效能目標<br>• **方案 2**: 參考業界標準 (如 P95 < 1s)<br>• **方案 3**: 先建立基準測試,後續定義目標<br>• **方案 4**: 暫時跳過效能測試,聚焦功能測試 | +0.5-1 小時 |

### 無測試環境時的應對流程

若完全沒有測試環境,建議採用「**快速環境搭建策略**」:

#### 方案 A: Docker Compose 本地環境 (推薦) - 2-4 小時

```yaml
# docker-compose.test.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      NODE_ENV: test
      DATABASE_URL: postgresql://postgres:test@db/test_db
    depends_on:
      - db
      - redis

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: test_db
      POSTGRES_PASSWORD: test
    tmpfs:
      - /var/lib/postgresql/data  # 使用記憶體,加速測試

  redis:
    image: redis:7-alpine
```

**優點**: 快速、可重現、成本低
**適用**: 大多數 Web/API 專案

#### 方案 B: 雲端測試環境 - 1-2 天

使用雲服務商免費試用:
- **AWS Free Tier**: EC2 + RDS
- **GCP Free Tier**: Compute Engine + Cloud SQL
- **Heroku**: 免費 Dyno (適合小型專案)

**優點**: 接近生產環境
**適用**: 需要真實雲端環境的專案

#### 方案 C: Mock 所有外部依賴 - 1-2 小時

```javascript
// 使用 Jest Mock
jest.mock('../services/paymentService', () => ({
  processPayment: jest.fn().mockResolvedValue({ success: true, transactionId: 'mock-123' })
}));

jest.mock('../services/emailService', () => ({
  sendEmail: jest.fn().mockResolvedValue(true)
}));

// 測試中使用
test('should process order successfully', async () => {
  const order = await createOrder(orderData);
  expect(order.status).toBe('confirmed');
  expect(paymentService.processPayment).toHaveBeenCalled();
});
```

**優點**: 極快、無依賴
**缺點**: 無法測試真實整合
**適用**: 單元測試、API Contract Testing

### 無測試資料時的應對流程

若缺少測試資料,建議採用「**測試資料生成策略**」:

#### 階段 1: 最小資料集 (Minimal Dataset) - 1 小時

手動建立核心測試資料:
- 1-2 個測試使用者
- 5-10 筆基礎資料 (商品、訂單等)
- 涵蓋 Happy Path 即可

#### 階段 2: Faker 自動生成 - 2-3 小時

```javascript
const { faker } = require('@faker-js/faker');

// 生成測試使用者
function generateUser() {
  return {
    email: faker.internet.email(),
    name: faker.person.fullName(),
    phone: faker.phone.number('+886-9##-###-###'),
    address: faker.location.streetAddress()
  };
}

// 批次生成 100 筆
const testUsers = Array.from({ length: 100 }, () => generateUser());
```

#### 階段 3: 生產資料匿名化 - 4-6 小時

```sql
-- 匿名化生產資料用於測試
UPDATE users SET
  email = CONCAT('test_', id, '@example.com'),
  name = CONCAT('Test User ', id),
  phone = CONCAT('+886-9', LPAD(id, 8, '0'))
WHERE environment = 'staging';
```

### 無 CI/CD 配置時的快速啟動

若缺少 CI/CD,建議採用「**GitHub Actions 快速模板**」:

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: npm ci

      - name: Run tests
        run: npm test -- --coverage

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

**時間**: 30 分鐘
**效果**: 自動執行測試、覆蓋率報告

---

## 🛠️ 免費工具替代方案

> 💡 **成本考量**: 商業測試工具價格高昂（Selenium Grid Enterprise, BrowserStack $3k+/月），以下提供功能相近的免費/開源替代方案。

### 測試工具對照表

| 工具類別 | 商業方案 | 免費/開源替代 | 功能對比 | 適用場景 |
|---------|---------|-------------|---------|---------|
| **E2E 測試框架** | TestComplete<br>Ranorex | **Playwright**<br>**Cypress**<br>**Selenium** | 功能完整,免費<br>缺少: 商業支援 | 所有 Web 測試場景<br>跨瀏覽器測試 |
| **API 測試** | Postman Pro<br>SoapUI Pro | **Postman Free**<br>**Rest-Assured**<br>**Supertest** | 基本功能免費<br>進階功能付費 | API 自動化測試<br>Contract Testing |
| **效能測試** | LoadRunner<br>NeoLoad | **k6**<br>**Gatling**<br>**JMeter** | 功能齊全,免費<br>缺少: GUI 易用性 | 負載測試<br>壓力測試 |
| **行動測試** | BrowserStack<br>Sauce Labs | **Appium**<br>**Detox**<br>**Android Emulator/iOS Simulator** | 本地測試免費<br>雲端測試需付費 | Mobile App 測試<br>跨裝置測試 |
| **測試報告** | Allure Enterprise<br>ReportPortal Cloud | **Allure Open Source**<br>**ReportPortal Self-Hosted**<br>**Mochawesome** | 開源版功能完整<br>需自行架設 | 測試結果視覺化<br>歷史趨勢分析 |
| **視覺回歸測試** | Percy<br>Chromatic | **BackstopJS**<br>**Puppeteer + Pixelmatch**<br>**jest-image-snapshot** | 本地測試免費<br>缺少: 雲端管理 | UI 變更檢測<br>跨瀏覽器比對 |
| **Contract Testing** | Pactflow | **Pact**<br>**Spring Cloud Contract** | 開源版完全免費<br>缺少: 雲端 Broker | 微服務 API 契約<br>前後端分離 |
| **Mutation Testing** | Stryker Dashboard | **Stryker**<br>**PIT (Java)** | 本地執行免費<br>雲端儀表板付費 | 測試品質驗證<br>測試覆蓋率盲點 |

### 工具安裝與使用指南

#### 1. Playwright（現代化 E2E 測試框架）

**安裝**:
```bash
npm init playwright@latest

# 或手動安裝
npm install -D @playwright/test
npx playwright install  # 下載瀏覽器
```

**基本測試範例**:
```javascript
// tests/login.spec.js
const { test, expect } = require('@playwright/test');

test('should login successfully', async ({ page }) => {
  await page.goto('https://example.com/login');

  await page.fill('[data-testid="email"]', 'user@example.com');
  await page.fill('[data-testid="password"]', 'password123');
  await page.click('[data-testid="login-btn"]');

  await expect(page).toHaveURL('/dashboard');
  await expect(page.locator('[data-testid="user-name"]'))
    .toContainText('Welcome');
});
```

**執行測試**:
```bash
# 執行所有測試
npx playwright test

# 執行特定測試
npx playwright test tests/login.spec.js

# Debug 模式
npx playwright test --debug

# 產生報告
npx playwright test --reporter=html
```

**CI/CD 整合**:
```yaml
# .github/workflows/playwright.yml
name: Playwright Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - name: Install dependencies
        run: npm ci
      - name: Install Playwright Browsers
        run: npx playwright install --with-deps
      - name: Run Playwright tests
        run: npx playwright test
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: playwright-report/
```

#### 2. k6（高效能負載測試）

**安裝**:
```bash
# macOS
brew install k6

# Linux
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6

# Docker
docker pull grafana/k6
```

**負載測試腳本**:
```javascript
// load-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 50 },   // 爬升到 50 個虛擬使用者
    { duration: '3m', target: 50 },   // 維持 50 個使用者
    { duration: '1m', target: 100 },  // 爬升到 100
    { duration: '3m', target: 100 },  // 維持 100
    { duration: '1m', target: 0 },    // 降回 0
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% 請求需 <500ms
    http_req_failed: ['rate<0.01'],   // 錯誤率 <1%
  },
};

export default function () {
  const res = http.get('https://api.example.com/users');

  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });

  sleep(1);
}
```

**執行測試**:
```bash
# 執行測試
k6 run load-test.js

# 輸出結果到 InfluxDB + Grafana
k6 run --out influxdb=http://localhost:8086/k6 load-test.js
```

**📊 效能基準值設定模板 (P50/P95/P99)** 🆕 (v0.01 新增)

> **為什麼需要 P50/P95/P99？**
> - P50 (中位數)：一般使用者體驗
> - P95：95% 使用者的體驗上限
> - P99：極端情況下的最慢響應

**效能基準值定義模板**：

| API 端點 | P50 | P95 | P99 | 錯誤率 | 說明 |
|---------|-----|-----|-----|-------|------|
| **登入 API** | < 200ms | < 500ms | < 1s | < 0.1% | 安全敏感，需快速回應 |
| **列表查詢** | < 300ms | < 800ms | < 2s | < 0.5% | 分頁查詢，可接受稍慢 |
| **詳情查詢** | < 150ms | < 400ms | < 1s | < 0.1% | 快取熱點，應極快 |
| **新增/修改** | < 500ms | < 1s | < 3s | < 0.5% | 包含驗證，可稍慢 |
| **檔案上傳** | < 2s | < 5s | < 10s | < 1% | 依檔案大小調整 |

**k6 完整閾值配置範例**：
```javascript
export const options = {
  thresholds: {
    // 全局指標
    http_req_duration: [
      'p(50)<300',    // P50 < 300ms
      'p(95)<800',    // P95 < 800ms
      'p(99)<2000',   // P99 < 2s
    ],
    http_req_failed: ['rate<0.01'],  // 錯誤率 < 1%

    // 依端點分類
    'http_req_duration{endpoint:login}': ['p(95)<500'],
    'http_req_duration{endpoint:list}': ['p(95)<800'],
    'http_req_duration{endpoint:detail}': ['p(95)<400'],

    // 吞吐量
    http_reqs: ['rate>100'],  // 至少 100 RPS
  },
};
```

**依應用類型的基準參考**：

| 應用類型 | P50 | P95 | P99 | 參考依據 |
|---------|-----|-----|-----|---------|
| **電商網站** | < 200ms | < 500ms | < 1s | Google RAIL |
| **金融系統** | < 100ms | < 300ms | < 500ms | 高 SLA 要求 |
| **內部工具** | < 500ms | < 1s | < 3s | 可接受較慢 |
| **API Gateway** | < 50ms | < 100ms | < 200ms | 純轉發，應極快 |
| **批次處理** | N/A | N/A | N/A | 以完成時間計 |

**效能退化告警閾值**：
```yaml
# 建議設定效能退化告警 (相對基準)
alerts:
  - name: performance_degradation
    condition: p95_current > p95_baseline * 1.2  # P95 退化超過 20%
    severity: warning

  - name: severe_degradation
    condition: p95_current > p95_baseline * 1.5  # P95 退化超過 50%
    severity: critical
```

**🆕 API Rate Limiting / 流量控制測試指引** (v0.01 補充)

> **為什麼需要 Rate Limiting 測試？**
> - 防止 API 被惡意或意外大量調用導致服務降級
> - 驗證限流策略（Token Bucket、Sliding Window）正確運作
> - 確保限流觸發時回應正確的 HTTP 429 狀態碼

**Rate Limiting 測試矩陣**：

| 測試項目 | 驗證重點 | 預期結果 |
|---------|---------|---------|
| **正常流量** | 低於限制的請求數 | 全部 200 OK |
| **邊界流量** | 恰好等於限制值 | 最後一筆 200 OK |
| **超限流量** | 超過限制的請求 | HTTP 429 + Retry-After header |
| **限流恢復** | 等待冷卻期後重試 | 恢復正常 200 OK |
| **分散式限流** | 多節點共享計數 | 總請求數不超過全域限制 |

**k6 Rate Limiting 測試範例**：
```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  scenarios: {
    rate_limit_test: {
      executor: 'constant-arrival-rate',
      rate: 120,          // 每秒 120 次請求（假設限制 100/s）
      timeUnit: '1s',
      duration: '10s',
      preAllocatedVUs: 50,
    },
  },
};

export default function () {
  const res = http.get('http://api.example.com/products');

  if (res.status === 429) {
    check(res, {
      'rate limit 回應包含 Retry-After': (r) => r.headers['Retry-After'] !== undefined,
      'rate limit 回應 body 包含錯誤訊息': (r) => r.json().error !== undefined,
    });
  } else {
    check(res, {
      'status is 200': (r) => r.status === 200,
    });
  }
}
```

**Spring Boot Rate Limiting 驗證（JUnit 5）**：
```java
@Test
void shouldReturn429WhenRateLimitExceeded() throws Exception {
    // 快速發送超過限制的請求
    int rateLimit = 100;
    for (int i = 0; i < rateLimit; i++) {
        mockMvc.perform(get("/api/products"))
               .andExpect(status().isOk());
    }
    // 超限請求應回傳 429
    mockMvc.perform(get("/api/products"))
           .andExpect(status().isTooManyRequests())
           .andExpect(header().exists("Retry-After"));
}
```

---

#### 3. Allure（開源測試報告框架）

**安裝**:
```bash
# macOS
brew install allure

# Linux
sudo apt-add-repository ppa:qameta/allure
sudo apt-get update
sudo apt-get install allure

# npm
npm install -g allure-commandline
```

**與測試框架整合**:
```bash
# Jest
npm install -D jest-allure

# Playwright
npm install -D allure-playwright

# Cypress
npm install -D @shelex/cypress-allure-plugin
```

**Playwright 範例**:
```javascript
// playwright.config.js
module.exports = {
  reporter: [
    ['allure-playwright'],
    ['html']
  ],
};
```

**產生報告**:
```bash
# 執行測試（產生結果）
npx playwright test

# 產生並開啟報告
allure generate ./allure-results --clean -o ./allure-report
allure open ./allure-report
```

#### 4. BackstopJS（視覺回歸測試）

**安裝**:
```bash
npm install -g backstopjs
```

**初始化配置**:
```bash
backstop init
```

**配置檔案 (backstop.json)**:
```json
{
  "id": "my_project",
  "viewports": [
    { "label": "phone", "width": 375, "height": 667 },
    { "label": "tablet", "width": 768, "height": 1024 },
    { "label": "desktop", "width": 1920, "height": 1080 }
  ],
  "scenarios": [
    {
      "label": "Homepage",
      "url": "http://localhost:3000",
      "delay": 500,
      "misMatchThreshold": 0.1
    },
    {
      "label": "Product Page",
      "url": "http://localhost:3000/products/123",
      "clickSelector": ".product-image",
      "delay": 1000
    }
  ],
  "paths": {
    "bitmaps_reference": "backstop_data/bitmaps_reference",
    "bitmaps_test": "backstop_data/bitmaps_test",
    "html_report": "backstop_data/html_report"
  },
  "engine": "puppeteer"
}
```

**執行測試**:
```bash
# 建立基準快照
backstop reference

# 執行測試（對比）
backstop test

# 批准變更（更新基準）
backstop approve
```

#### 5. Pact（Contract Testing）

**安裝**:
```bash
npm install -D @pact-foundation/pact
```

**Consumer 測試範例**:
```javascript
// consumer.spec.js
const { Pact } = require('@pact-foundation/pact');
const path = require('path');

const provider = new Pact({
  consumer: 'FrontendApp',
  provider: 'UserService',
  port: 1234,
  log: path.resolve(process.cwd(), 'logs', 'pact.log'),
  dir: path.resolve(process.cwd(), 'pacts'),
});

describe('User Service Contract', () => {
  beforeAll(() => provider.setup());
  afterAll(() => provider.finalize());

  it('should get user by ID', async () => {
    await provider.addInteraction({
      state: 'user 123 exists',
      uponReceiving: 'a request for user 123',
      withRequest: {
        method: 'GET',
        path: '/users/123',
      },
      willRespondWith: {
        status: 200,
        body: {
          id: 123,
          name: 'John Doe',
          email: 'john@example.com',
        },
      },
    });

    const response = await fetch('http://localhost:1234/users/123');
    const user = await response.json();

    expect(user.id).toBe(123);
    expect(user.name).toBe('John Doe');
  });
});
```

#### 6. Stryker（Mutation Testing）

**安裝**:
```bash
npm install -D @stryker-mutator/core
npx stryker init
```

**配置 (stryker.conf.json)**:
```json
{
  "$schema": "./node_modules/@stryker-mutator/core/schema/stryker-schema.json",
  "testRunner": "jest",
  "coverageAnalysis": "perTest",
  "mutate": [
    "src/**/*.js",
    "!src/**/*.spec.js"
  ]
}
```

**執行 Mutation Testing**:
```bash
npx stryker run
```

**📊 Mutation Testing 進階配置與解讀指引** 🆕 (v0.01 擴展)

**Mutation 類型說明**：

| Mutation 類型 | 說明 | 範例 |
|--------------|------|------|
| **ConditionalBoundary** | 邊界條件變異 | `<` → `<=`, `>` → `>=` |
| **ArithmeticOperator** | 算術運算變異 | `+` → `-`, `*` → `/` |
| **EqualityOperator** | 相等性變異 | `===` → `!==` |
| **LogicalOperator** | 邏輯運算變異 | `&&` → `\|\|` |
| **StringLiteral** | 字串變異 | `"hello"` → `""` |
| **BooleanLiteral** | 布林值變異 | `true` → `false` |

**進階配置範例**：
```json
{
  "$schema": "./node_modules/@stryker-mutator/core/schema/stryker-schema.json",
  "testRunner": "jest",
  "coverageAnalysis": "perTest",
  "mutate": [
    "src/**/*.js",
    "!src/**/*.spec.js",
    "!src/**/*.test.js"
  ],
  "thresholds": {
    "high": 80,
    "low": 60,
    "break": 50
  },
  "concurrency": 4,
  "timeoutMS": 10000,
  "reporters": ["html", "clear-text", "progress"]
}
```

**Mutation Score 解讀**：

| 分數範圍 | 評級 | 說明 | 建議行動 |
|---------|------|------|---------|
| **80-100%** | ✅ 優秀 | 測試品質高，大部分邏輯有有效測試 | 維持現狀 |
| **60-79%** | ⚠️ 良好 | 測試覆蓋尚可，但有盲點 | 針對 Survived Mutants 補測試 |
| **40-59%** | 🟡 待改進 | 測試品質不足 | 優先補強核心邏輯測試 |
| **< 40%** | 🔴 差 | 測試幾乎無效 | 重新檢視測試策略 |

**常見 Survived Mutants 處理**：

| Survived 類型 | 可能原因 | 解決方案 |
|--------------|---------|---------|
| 邊界條件 | 未測試邊界值 | 新增 boundary value test |
| 字串變異 | 未驗證字串內容 | 新增 assertion 驗證 |
| 邏輯運算 | 分支未覆蓋 | 新增 branch coverage test |
| 算術運算 | 計算結果未驗證 | 新增 result verification |

**CI/CD 整合建議**：
```yaml
# 在 CI 中僅對變更檔案執行 Mutation Testing
mutation-test:
  runs-on: ubuntu-latest
  if: github.event_name == 'pull_request'
  steps:
    - run: |
        CHANGED_FILES=$(git diff --name-only origin/main)
        npx stryker run --mutate "$CHANGED_FILES"
```

---

### 完整測試 CI/CD Pipeline 範例

```yaml
# .github/workflows/complete-testing.yml
name: Complete Testing Suite

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm ci
      - run: npm test -- --coverage
      - uses: codecov/codecov-action@v3

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
    steps:
      - uses: actions/checkout@v3
      - run: npm ci
      - run: npm run test:integration

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npm run build
      - run: npm start &
      - run: npx wait-on http://localhost:3000
      - run: npx playwright test
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: playwright-report/

  visual-regression:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: npm ci
      - run: npm start &
      - run: npx wait-on http://localhost:3000
      - run: npx backstop test
      - uses: actions/upload-artifact@v3
        if: failure()
        with:
          name: backstop-report
          path: backstop_data/html_report/

  performance-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: grafana/k6-action@v0.3.0
        with:
          filename: tests/load-test.js
```

### 工具選擇建議

| 測試類型 | 小型專案 (<10人) | 中型專案 (10-50人) | 大型專案 (50+人) |
|---------|-----------------|-------------------|-----------------|
| **E2E 測試** | Playwright | Playwright + Allure | Playwright + Allure + ReportPortal |
| **API 測試** | Supertest | Rest-Assured | Rest-Assured + Pact |
| **效能測試** | k6 | k6 + InfluxDB + Grafana | k6 + Grafana Cloud |
| **視覺測試** | BackstopJS | BackstopJS 或 Percy Free | Percy/Chromatic 付費 |
| **行動測試** | 本地模擬器 | Appium + 本地裝置農場 | BrowserStack (付費) |

### 成本對比

| 方案 | 年度成本 | 工具組合 | 適用團隊 |
|------|---------|---------|---------|
| **完全免費** | $0 | Playwright + k6 + BackstopJS + Allure | 小型團隊 |
| **混合方案** | $3k-10k | 免費工具 + BrowserStack Basic | 中型團隊 |
| **商業方案** | $50k+ | TestComplete + LoadRunner + BrowserStack | 大型企業 |

---

## 🔒 CI/CD 安全基線與增強掃描（強制前置）

> **⚠️ CRITICAL**: 開始測試工作前，必須確認 CI/CD Pipeline 已配置以下安全層級。
> **Testing 情境安全等級: Standard** (L0 + L1 + SAST)

### Layer 0: Security Baseline（強制）

所有 PR 必須通過以下檢查：

| 檢查項 | 工具 | 阻塞等級 |
|--------|------|---------|
| Secret Detection | TruffleHog / gitleaks | 🔴 永遠阻塞 |
| Dependency Scan (SCA) | Trivy / npm audit | 🔴 Critical/High 阻塞 |
| License Compliance | license-checker | ⚠️ GPL-3.0/AGPL 阻塞 |

📖 **配置範本**: [Layer0_Security_Baseline_Template.md](../../docs_template/scenario_specific/devops/Layer0_Security_Baseline_Template.md)

### Layer 1: Build & Verify（強制）

| 關卡 | 目的 | 阻塞等級 |
|------|------|---------|
| Lint + Format | 程式碼風格一致性 | 🔴 失敗阻塞 |
| Compile / Build | 編譯成功 | 🔴 失敗阻塞 |
| Unit Test + Coverage | 覆蓋率 ≥ 80% | 🔴 失敗阻塞 |

📖 **配置範本**: [Layer1_Build_Verify_Template.md](../../docs_template/scenario_specific/devops/Layer1_Build_Verify_Template.md)

### 增強安全掃描: SAST（Standard 等級）

測試代碼本身也需要品質保證，SAST 確保測試工具和腳本無安全漏洞。

| 掃描類型 | 工具 | 阻塞策略 |
|---------|------|---------|
| **SAST** | Semgrep / CodeQL | 🔴 Critical/High 阻塞 |

📖 **配置範本**: [Security_Scan_Integration_Template.md](../../docs_template/scenario_specific/devops/Security_Scan_Integration_Template.md)

- [ ] Layer 0 Security Baseline 已配置
- [ ] Layer 1 Build & Verify 已配置
- [ ] SAST 掃描已配置（Semgrep 或 CodeQL）

---

## 🚀 完整執行流程

### 階段 1：測試策略制定 (40-60 分鐘)

#### 步驟 1.1：測試金字塔設計 (QA-Lead)

**標準測試金字塔**：
```
         /\        E2E Tests (10%)
        /  \       - 全流程測試
       /----\      - UI 自動化測試
      /      \
     /--------\    Integration Tests (30%)
    /          \   - API 測試
   /            \  - 資料庫整合測試
  /--------------\ - 第三方服務整合測試
 /                \
/------------------\ Unit Tests (60%)
                     - 函式/類別測試
                     - 邏輯驗證
                     - 邊界條件
```

**測試類型與工具選擇**：

| 測試類型 | 目的 | 工具範例 | 執行頻率 |
|---------|------|---------|---------|
| **單元測試** | 驗證單一函式/模組 | Jest, Mocha, pytest, JUnit | 每次提交 |
| **整合測試** | 驗證模組間整合 | Supertest, TestContainers | 每次提交 |
| **E2E 測試** | 驗證完整使用者流程 | Playwright, Cypress, Selenium | 每次部署前 |
| **API 測試** | 驗證 API 契約和行為 | Postman, Rest-Assured, Pact | 每次提交 |
| **效能測試** | 驗證系統效能 | k6, JMeter, Gatling | 每週/每次重大變更 |
| **安全性測試** | 發現安全漏洞 | OWASP ZAP, Burp Suite | 每次發布前 |
| **無障礙測試** | 驗證無障礙性 | axe, Lighthouse | 每次 UI 變更 |
| **視覺回歸測試** | 檢測 UI 變化 | Percy, Chromatic | 每次 UI 變更 |

> **⚠️ Percy / Chromatic 視覺回歸測試指南 (Visual Regression Testing)**
>
> 視覺回歸測試自動檢測 UI 變化,避免意外破壞外觀:
>
> **工具比較**:
> | 特性 | Percy | Chromatic | 開源替代方案 |
> |------|-------|-----------|------------|
> | **定價** | 免費: 5000 screenshots/月 | 免費: 5000 snapshots/月 | BackstopJS (完全免費) |
> | **框架支援** | React, Vue, Angular, Static HTML | Storybook 專用 | 通用 (Puppeteer-based) |
> | **CI/CD 整合** | GitHub, GitLab, CircleCI | GitHub, GitLab | 需自行配置 |
> | **審查介面** | Web-based | Web-based | 本地 HTML 報告 |
> | **適用場景** | 通用 Web 專案 | Component-driven 專案 | 預算有限專案 |
>
> **範例 1: Percy 整合 (React + Cypress)**
> ```javascript
> // cypress/e2e/visual-tests.cy.js
> import "@percy/cypress";
> 
> describe("Visual Regression Tests", () => {
>   it("Homepage should match snapshot", () => {
>     cy.visit("/");
>     cy.percySnapshot("Homepage");
>   });
>   
>   it("Login page should match snapshot", () => {
>     cy.visit("/login");
>     cy.percySnapshot("Login Page");
>   });
>   
>   it("Dashboard with different user roles", () => {
>     cy.login("admin@example.com");
>     cy.visit("/dashboard");
>     cy.percySnapshot("Dashboard - Admin", {
>       widths: [375, 768, 1280],  // 測試多種螢幕寬度
>       minHeight: 1024
>     });
>   });
> });
> ```
>
> **範例 2: Chromatic 整合 (Storybook)**
> ```javascript
> // .storybook/main.js
> module.exports = {
>   stories: ["../src/**/*.stories.@(js|jsx|ts|tsx)"],
>   addons: ["@storybook/addon-essentials"]
> };
> 
> // src/components/Button.stories.tsx
> import { Button } from "./Button";
> 
> export default {
>   title: "Components/Button",
>   component: Button
> };
> 
> export const Primary = {
>   args: { variant: "primary", children: "Click me" }
> };
> 
> export const Secondary = {
>   args: { variant: "secondary", children: "Cancel" }
> };
> 
> export const Disabled = {
>   args: { variant: "primary", disabled: true, children: "Disabled" }
> };
> 
> // package.json
> {
>   "scripts": {
>     "chromatic": "chromatic --project-token=${CHROMATIC_PROJECT_TOKEN}"
>   }
> }
> ```
>
> **範例 3: BackstopJS (開源方案)**
> ```javascript
> // backstop.config.js
> module.exports = {
>   id: "my_project",
>   viewports: [
>     { label: "phone", width: 375, height: 667 },
>     { label: "tablet", width: 768, height: 1024 },
>     { label: "desktop", width: 1920, height: 1080 }
>   ],
>   scenarios: [
>     {
>       label: "Homepage",
>       url: "http://localhost:3000",
>       delay: 500,  // 等待動畫完成
>       misMatchThreshold: 0.1  // 0.1% 差異容忍度
>     },
>     {
>       label: "Product Page",
>       url: "http://localhost:3000/products/123",
>       clickSelector: ".product-image",  // 點擊展開
>       delay: 1000
>     }
>   ],
>   paths: {
>     bitmaps_reference: "backstop_data/bitmaps_reference",
>     bitmaps_test: "backstop_data/bitmaps_test",
>     html_report: "backstop_data/html_report"
>   },
>   engine: "puppeteer",
>   report: ["browser", "CI"]
> };
> ```
>
> **CI/CD 整合範例**:
> ```yaml
> # .github/workflows/visual-tests.yml
> name: Visual Regression Tests
> 
> on: [pull_request]
> 
> jobs:
>   percy:
>     runs-on: ubuntu-latest
>     steps:
>       - uses: actions/checkout@v3
>       
>       - name: Install dependencies
>         run: npm ci
>       
>       - name: Build Storybook
>         run: npm run build-storybook
>       
>       - name: Run Percy
>         run: npx percy storybook ./storybook-static
>         env:
>           PERCY_TOKEN: \${{ secrets.PERCY_TOKEN }}
>       
>       # 或使用 Chromatic
>       - name: Run Chromatic
>         uses: chromaui/action@v1
>         with:
>           projectToken: \${{ secrets.CHROMATIC_PROJECT_TOKEN }}
>           buildScriptName: build-storybook
> ```
>
> **最佳實踐**:
> - ✅ **分層測試**: 元件級 (Storybook) + 頁面級 (E2E)
> - ✅ **多螢幕測試**: 手機、平板、桌面
> - ✅ **等待動畫**: 設定適當 delay,避免動畫中間態
> - ✅ **容忍度設定**: misMatchThreshold 0.1-1% (避免過於敏感)
> - ✅ **基準更新**: 故意變更 UI 時,更新基準快照 (approve changes)
> - ⚠️ **避免動態內容**: 隱藏時間戳、隨機 ID
> - ⚠️ **控制測試範圍**: 不要對每個頁面都做視覺測試,聚焦關鍵頁面

| **視覺回歸測試** | 檢測 UI 變化 | Percy, Chromatic | 每次 UI 變更 |

**測試範圍規劃**：
```javascript
// 測試覆蓋率目標
{
  "overall": "≥ 80%",         // 整體覆蓋率
  "critical": "100%",          // 關鍵業務邏輯
  "statements": "≥ 80%",
  "branches": "≥ 75%",
  "functions": "≥ 80%",
  "lines": "≥ 80%"
}
```

> 🔴 **人機協作點**: 測試策略制定確認
> - 確認測試金字塔比例（60% 單元 / 30% 整合 / 10% E2E）
> - 確認測試覆蓋率目標（整體 ≥ 80%，關鍵業務 100%）
> - 確認測試工具選擇與技術棧相容性
> - 確認自動化程度目標和時程規劃

---

### 階段 2：測試案例設計 (1-1.5 小時)

#### 步驟 2.1：測試案例生成 (QA-Lead + QA-Automation)

**單元測試範例**：
```javascript
// userService.test.js
describe('UserService', () => {
  describe('createUser', () => {
    it('should create user with valid data', async () => {
      const userData = {
        email: 'test@example.com',
        password: 'SecurePass123!',
        name: 'Test User'
      };

      const user = await userService.createUser(userData);

      expect(user.id).toBeDefined();
      expect(user.email).toBe(userData.email);
      expect(user.password).not.toBe(userData.password); // 應加密
    });

    it('should reject invalid email', async () => {
      const userData = { email: 'invalid-email', password: 'Pass123!', name: 'Test' };

      await expect(userService.createUser(userData))
        .rejects
        .toThrow('Invalid email format');
    });

    it('should reject weak password', async () => {
      const userData = { email: 'test@example.com', password: '123', name: 'Test' };

      await expect(userService.createUser(userData))
        .rejects
        .toThrow('Password too weak');
    });

    it('should prevent duplicate email', async () => {
      const userData = { email: 'existing@example.com', password: 'Pass123!', name: 'Test' };

      await expect(userService.createUser(userData))
        .rejects
        .toThrow('Email already exists');
    });
  });
});
```

**API 測試範例**：
```javascript
// api/users.test.js
const request = require('supertest');
const app = require('../app');

describe('POST /api/users', () => {
  it('should create user and return 201', async () => {
    const response = await request(app)
      .post('/api/users')
      .send({
        email: 'newuser@example.com',
        password: 'SecurePass123!',
        name: 'New User'
      })
      .expect(201)
      .expect('Content-Type', /json/);

    expect(response.body.user.id).toBeDefined();
    expect(response.body.user.email).toBe('newuser@example.com');
    expect(response.body.token).toBeDefined();
  });

  it('should return 400 for invalid data', async () => {
    await request(app)
      .post('/api/users')
      .send({ email: 'invalid' })
      .expect(400);
  });

  it('should return 409 for duplicate email', async () => {
    await request(app)
      .post('/api/users')
      .send({ email: 'existing@example.com', password: 'Pass123!', name: 'Test' })
      .expect(409);
  });
});
```

**E2E 測試範例 (Playwright)**：
```javascript
// e2e/user-registration.spec.js
import { test, expect } from '@playwright/test';

test.describe('User Registration Flow', () => {
  test('should complete registration successfully', async ({ page }) => {
    // 1. 訪問註冊頁面
    await page.goto('/register');

    // 2. 填寫表單
    await page.fill('[data-testid="email-input"]', 'test@example.com');
    await page.fill('[data-testid="password-input"]', 'SecurePass123!');
    await page.fill('[data-testid="name-input"]', 'Test User');

    // 3. 提交表單
    await page.click('[data-testid="submit-button"]');

    // 4. 驗證成功訊息
    await expect(page.locator('[data-testid="success-message"]'))
      .toContainText('Registration successful');

    // 5. 驗證跳轉到首頁
    await expect(page).toHaveURL('/dashboard');

    // 6. 驗證使用者已登入
    await expect(page.locator('[data-testid="user-name"]'))
      .toContainText('Test User');
  });

  test('should show error for invalid email', async ({ page }) => {
    await page.goto('/register');
    await page.fill('[data-testid="email-input"]', 'invalid-email');
    await page.fill('[data-testid="password-input"]', 'SecurePass123!');
    await page.click('[data-testid="submit-button"]');

    await expect(page.locator('[data-testid="error-message"]'))
      .toContainText('Invalid email format');
  });
});
```

**🆕 Java / Spring Boot 測試範例** (v0.01 補充)

> 後端使用 Spring Boot 的專案，以下為 JUnit 5 + Mockito + Spring Boot Test 的對應測試寫法。

**單元測試 (JUnit 5 + Mockito)**：
```java
// UserServiceTest.java
@ExtendWith(MockitoExtension.class)
class UserServiceTest {

    @Mock private UserRepository userRepository;
    @Mock private PasswordEncoder passwordEncoder;
    @InjectMocks private UserService userService;

    @Test
    void shouldCreateUserWithValidData() {
        // Arrange
        UserCreateDto dto = new UserCreateDto("test@example.com", "SecurePass123!", "Test User");
        when(userRepository.existsByEmail(dto.getEmail())).thenReturn(false);
        when(passwordEncoder.encode(dto.getPassword())).thenReturn("encoded_hash");
        when(userRepository.save(any(User.class))).thenAnswer(inv -> {
            User u = inv.getArgument(0);
            u.setId(1L);
            return u;
        });

        // Act
        User result = userService.createUser(dto);

        // Assert
        assertNotNull(result.getId());
        assertEquals("test@example.com", result.getEmail());
        assertNotEquals("SecurePass123!", result.getPassword()); // 應已加密
        verify(userRepository).save(any(User.class));
    }

    @Test
    void shouldRejectDuplicateEmail() {
        UserCreateDto dto = new UserCreateDto("existing@example.com", "Pass123!", "Test");
        when(userRepository.existsByEmail(dto.getEmail())).thenReturn(true);

        assertThrows(DuplicateEmailException.class, () -> userService.createUser(dto));
    }

    @Test
    void shouldRejectWeakPassword() {
        UserCreateDto dto = new UserCreateDto("test@example.com", "123", "Test");

        assertThrows(WeakPasswordException.class, () -> userService.createUser(dto));
    }
}
```

**API 整合測試 (Spring Boot Test + MockMvc)**：
```java
// UserControllerIntegrationTest.java
@SpringBootTest
@AutoConfigureMockMvc
@Transactional  // 每個測試自動 rollback
class UserControllerIntegrationTest {

    @Autowired private MockMvc mockMvc;
    @Autowired private ObjectMapper objectMapper;

    @Test
    void shouldCreateUserAndReturn201() throws Exception {
        UserCreateDto dto = new UserCreateDto("newuser@example.com", "SecurePass123!", "New User");

        mockMvc.perform(post("/api/users")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(dto)))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.user.id").exists())
            .andExpect(jsonPath("$.user.email").value("newuser@example.com"))
            .andExpect(jsonPath("$.token").exists());
    }

    @Test
    void shouldReturn400ForInvalidData() throws Exception {
        mockMvc.perform(post("/api/users")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"email\": \"invalid\"}"))
            .andExpect(status().isBadRequest());
    }

    @Test
    void shouldReturn409ForDuplicateEmail() throws Exception {
        UserCreateDto dto = new UserCreateDto("existing@example.com", "Pass123!", "Test");

        mockMvc.perform(post("/api/users")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(dto)))
            .andExpect(status().isConflict());
    }
}
```

**Repository 測試 (Testcontainers + PostgreSQL)**：
```java
// UserRepositoryTest.java
@DataJpaTest
@Testcontainers
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
class UserRepositoryTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:18-alpine");

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }

    @Autowired private UserRepository userRepository;

    @Test
    void shouldFindUserByEmail() {
        User user = new User("test@example.com", "encoded", "Test User");
        userRepository.save(user);

        Optional<User> found = userRepository.findByEmail("test@example.com");

        assertTrue(found.isPresent());
        assertEquals("Test User", found.get().getName());
    }
}
```

**測試案例設計原則**：
- **AAA 模式**：Arrange (準備) → Act (執行) → Assert (驗證)
- **FIRST 原則**：Fast (快速)、Independent (獨立)、Repeatable (可重複)、Self-Validating (自我驗證)、Timely (及時)
- **Given-When-Then**：Given (前置條件) → When (執行動作) → Then (預期結果)

> 🔴 **人機協作點**: 測試案例設計確認
> - 確認測試案例的完整性（涵蓋正常/異常/邊界條件）
> - 審查測試案例優先級排序（P0/P1/P2）
> - 驗證測試案例可維護性（清晰的命名和結構）
> - 確認測試資料準備策略

---

### 階段 3：測試自動化實施 (1-1.5 小時)

#### 步驟 3.1：CI/CD 整合 (QA-Automation + DevOps)

**GitHub Actions 測試流程**：
```yaml
name: Test Pipeline

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: npm ci

      - name: Run unit tests
        run: npm run test:unit -- --coverage

      - name: Upload coverage
        uses: codecov/codecov-action@v3

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3

      - name: Run integration tests
        run: npm run test:integration
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3

      - name: Install Playwright
        run: npx playwright install --with-deps

      - name: Start application
        run: npm run start &

      - name: Wait for app to be ready
        run: npx wait-on http://localhost:3000

      - name: Run E2E tests
        run: npm run test:e2e

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: playwright-report/
```

**測試資料管理**：
```javascript
// test/fixtures/users.js
export const testUsers = {
  validUser: {
    email: 'valid@example.com',
    password: 'SecurePass123!',
    name: 'Valid User'
  },

  adminUser: {
    email: 'admin@example.com',
    password: 'AdminPass123!',
    name: 'Admin User',
    role: 'admin'
  },

  invalidEmail: {
    email: 'invalid-email',
    password: 'SecurePass123!',
    name: 'Invalid User'
  }
};

// test/setup.js - 測試前清理和準備
beforeEach(async () => {
  await db.users.deleteMany({}); // 清空測試資料
  await db.users.insert(testUsers.adminUser); // 插入固定測試資料
});
```

> **⚠️ 測試資料生成工具和策略 (Test Data Generation)**
>
> 大量測試資料準備需要專業工具和策略,避免手動維護:
>
> **工具 1: Faker.js (通用假資料生成器)**
> ```javascript
> const { faker } = require("@faker-js/faker");
> 
> // 生成單筆使用者資料
> function generateUser() {
>   return {
>     id: faker.string.uuid(),
>     email: faker.internet.email(),
>     name: faker.person.fullName(),
>     phone: faker.phone.number("+886-9##-###-###"),
>     address: {
>       street: faker.location.streetAddress(),
>       city: faker.location.city(),
>       zipCode: faker.location.zipCode()
>     },
>     createdAt: faker.date.past({ years: 2 })
>   };
> }
> 
> // 批次生成 1000 筆
> const users = Array.from({ length: 1000 }, () => generateUser());
> ```
>
> **工具 2: Factory Bot / Fishery (Factory Pattern)**
> ```javascript
> // factories/user.factory.js
> const { Factory } = require("fishery");
> const { faker } = require("@faker-js/faker");
> 
> const UserFactory = Factory.define(({ sequence }) => ({
>   id: sequence,
>   email: faker.internet.email(),
>   name: faker.person.fullName(),
>   role: "user",
>   status: "active",
>   createdAt: new Date()
> }));
> 
> // 使用範例
> const user = UserFactory.build();  // 生成資料 (不存 DB)
> const users = UserFactory.buildList(100);  // 生成 100 筆
> 
> const adminUser = UserFactory.build({ role: "admin" });  // 覆蓋特定欄位
> const savedUser = await UserFactory.create();  // 生成並存入 DB
> ```
>
> **工具 3: 資料庫 Seeder (用於環境初始化)**
> ```javascript
> // seeds/test-data.seed.js
> const { faker } = require("@faker-js/faker");
> 
> async function seed(db) {
>   // 生成 1000 位使用者
>   const users = Array.from({ length: 1000 }, (_, i) => ({
>     id: i + 1,
>     email: `user${i}@test.com`,
>     name: faker.person.fullName(),
>     createdAt: faker.date.past({ years: 1 })
>   }));
>   await db.users.insertMany(users);
>   
>   // 生成 5000 筆訂單 (關聯到使用者)
>   const orders = Array.from({ length: 5000 }, (_, i) => ({
>     id: i + 1,
>     userId: faker.number.int({ min: 1, max: 1000 }),
>     amount: faker.number.float({ min: 10, max: 5000, precision: 0.01 }),
>     status: faker.helpers.arrayElement(["pending", "completed", "cancelled"]),
>     createdAt: faker.date.past({ years: 1 })
>   }));
>   await db.orders.insertMany(orders);
>   
>   console.log("✅ Test data seeded: 1000 users, 5000 orders");
> }
> 
> module.exports = { seed };
> ```
>
> **工具 4: 真實資料匿名化 (用於 Staging 環境)**
> ```sql
> -- SQL 範例：匿名化生產資料用於測試
> UPDATE users SET
>   email = CONCAT("test_", id, "@example.com"),
>   name = CONCAT("Test User ", id),
>   phone = CONCAT("+886-9", LPAD(id, 8, "0")),
>   address = "Test Address"
> WHERE environment = "staging";
> ```
>
> **策略 1: 分層測試資料 (Tiered Test Data)**
> ```yaml
> test_data_tiers:
>   # 微量資料 (單元測試)
>   minimal:
>     users: 5
>     orders: 10
>     execution_time: "< 1s"
>     use_case: "單元測試、快速驗證"
>   
>   # 中量資料 (整合測試)
>   medium:
>     users: 100
>     orders: 500
>     execution_time: "5-10s"
>     use_case: "API 整合測試、業務邏輯驗證"
>   
>   # 大量資料 (效能測試)
>   large:
>     users: 10000
>     orders: 100000
>     execution_time: "1-2 min"
>     use_case: "效能測試、壓力測試、分頁測試"
> ```
>
> **策略 2: 測試資料版本控制**
> ```bash
> # 使用 Git 管理測試資料 Snapshots
> test-data/
>   ├── snapshots/
>   │   ├── v1.0.0/
>   │   │   ├── users.json
>   │   │   └── orders.json
>   │   ├── v1.1.0/
>   │   │   ├── users.json
>   │   │   ├── orders.json
>   │   │   └── products.json  # 新增
>   ├── factories/
>   │   ├── user.factory.js
>   │   └── order.factory.js
>   └── seeds/
>       └── test-data.seed.js
> ```
>
> **策略 3: 自動化測試資料清理**
> ```javascript
> // tests/global-teardown.js
> module.exports = async () => {
>   const db = await connectToTestDB();
>   
>   // 保留少量基礎資料,刪除測試生成的資料
>   await db.users.deleteMany({ email: /^test_/ });
>   await db.orders.deleteMany({ createdAt: { $gte: testStartTime } });
>   
>   console.log("✅ Test data cleaned up");
> };
> ```
>
> **工具選擇建議**:
> | 語言/框架 | 推薦工具 | 適用場景 |
> |---------|---------|---------|
> | JavaScript/TypeScript | Faker.js + Fishery | 通用,功能完整 |
> | Python | Faker + Factory Boy | Django/Flask 專案 |
> | Java | JavaFaker + JPA Test Fixtures | Spring Boot 專案 |
> | Ruby | FactoryBot + FFaker | Rails 專案 |
> | Go | go-faker + testfixtures | Go 專案 |

```

**Mock 和 Stub**：
```javascript
// Mock 外部 API
jest.mock('../services/emailService', () => ({
  sendWelcomeEmail: jest.fn().mockResolvedValue(true)
}));

// 測試中使用
it('should send welcome email after registration', async () => {
  const emailService = require('../services/emailService');

  await userService.createUser(userData);

  expect(emailService.sendWelcomeEmail).toHaveBeenCalledWith(
    userData.email,
    expect.objectContaining({ name: userData.name })
  );
});
```

> 🔴 **人機協作點**: CI/CD 整合確認
> - 確認 CI/CD Pipeline 配置正確（測試自動觸發）
> - 驗證測試執行效能（建議 < 10 分鐘）
> - 確認測試失敗通知機制（Email/Slack）
> - 審查測試報告可讀性和完整性

---

### 階段 4：測試環境管理 (30-40 分鐘)

#### 步驟 4.1：環境隔離策略

**測試環境配置**：
```javascript
// config/test.config.js
module.exports = {
  database: {
    url: process.env.TEST_DATABASE_URL || 'postgresql://localhost/test_db',
    options: {
      logging: false // 測試時關閉 SQL 日誌
    }
  },

  redis: {
    url: process.env.TEST_REDIS_URL || 'redis://localhost:6379/1' // 使用不同 DB
  },

  email: {
    provider: 'mock', // 測試環境使用 Mock
  },

  features: {
    enableRateLimiting: false // 測試時關閉限流
  }
};
```

**Docker Compose 測試環境**：
```yaml
# docker-compose.test.yml
version: '3.8'

services:
  test-db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: test_db
      POSTGRES_PASSWORD: test_password
    tmpfs:
      - /var/lib/postgresql/data  # 使用記憶體，加速測試

  test-redis:
    image: redis:7-alpine

  test-runner:
    build: .
    depends_on:
      - test-db
      - test-redis
    environment:
      NODE_ENV: test
      DATABASE_URL: postgresql://postgres:test_password@test-db/test_db
      REDIS_URL: redis://test-redis:6379
    command: npm test
```

> **⚠️ 微服務架構測試環境配置 (Microservices Test Environment)**
>
> Docker Compose 適合簡單場景,微服務架構需更複雜的測試環境策略:
>
> **策略 1: 完整微服務叢集 (Full Cluster) - 用於整合測試**
> ```yaml
> # docker-compose.microservices.yml
> version: "3.8"
> 
> services:
>   # Service Mesh (可選)
>   istio-proxy:
>     image: istio/proxyv2:1.18.0
>     ports:
>       - "15000:15000"  # Envoy Admin
>   
>   # API Gateway
>   api-gateway:
>     build: ./services/gateway
>     ports:
>       - "3000:3000"
>     environment:
>       - NODE_ENV=test
>       - USER_SERVICE_URL=http://user-service:4001
>       - ORDER_SERVICE_URL=http://order-service:4002
>     depends_on:
>       - user-service
>       - order-service
>   
>   # User Service
>   user-service:
>     build: ./services/user
>     environment:
>       - DATABASE_URL=postgresql://postgres:test@user-db/users_test
>       - REDIS_URL=redis://redis:6379/0
>     depends_on:
>       - user-db
>       - redis
>   
>   # Order Service
>   order-service:
>     build: ./services/order
>     environment:
>       - DATABASE_URL=postgresql://postgres:test@order-db/orders_test
>       - MESSAGE_QUEUE_URL=amqp://rabbitmq:5672
>     depends_on:
>       - order-db
>       - rabbitmq
>   
>   # 資料庫 (每個服務獨立 DB)
>   user-db:
>     image: postgres:15-alpine
>     environment:
>       POSTGRES_DB: users_test
>       POSTGRES_PASSWORD: test
>     tmpfs:
>       - /var/lib/postgresql/data
>   
>   order-db:
>     image: postgres:15-alpine
>     environment:
>       POSTGRES_DB: orders_test
>       POSTGRES_PASSWORD: test
>     tmpfs:
>       - /var/lib/postgresql/data
>   
>   # 共享基礎設施
>   redis:
>     image: redis:7-alpine
>   
>   rabbitmq:
>     image: rabbitmq:3-management-alpine
>     ports:
>       - "15672:15672"  # Management UI
> ```
>
> **策略 2: 混合 Mock (Hybrid Mock) - 用於單一服務測試**
> ```javascript
> // 測試 Order Service 時,Mock 其他服務
> // tests/setup/mock-services.js
> const nock = require("nock");
> 
> function setupMockServices() {
>   // Mock User Service
>   nock("http://user-service:4001")
>     .get("/users/123")
>     .reply(200, {
>       id: 123,
>       name: "Test User",
>       email: "test@example.com"
>     })
>     .persist();
>   
>   // Mock Payment Service
>   nock("http://payment-service:4003")
>     .post("/payments")
>     .reply(200, { paymentId: "pay_123", status: "success" })
>     .persist();
> }
> 
> module.exports = { setupMockServices };
> ```
>
> **策略 3: Kubernetes Test Cluster (用於大型專案)**
> ```yaml
> # k8s/test-namespace.yml
> apiVersion: v1
> kind: Namespace
> metadata:
>   name: test-env
>   labels:
>     environment: test
>     auto-cleanup: "true"  # 自動清理
> ---
> # Deployment 範例
> apiVersion: apps/v1
> kind: Deployment
> metadata:
>   name: user-service
>   namespace: test-env
> spec:
>   replicas: 1  # 測試環境單一副本
>   selector:
>     matchLabels:
>       app: user-service
>   template:
>     metadata:
>       labels:
>         app: user-service
>     spec:
>       containers:
>       - name: user-service
>         image: user-service:test-${CI_COMMIT_SHA}
>         env:
>         - name: ENVIRONMENT
>           value: "test"
>         resources:
>           limits:
>             memory: "256Mi"  # 測試環境降低資源
>             cpu: "200m"
> ```
>
> **策略選擇指南**:
> | 專案規模 | 服務數量 | 推薦策略 | 啟動時間 |
> |---------|---------|---------|---------|
> | 小型 | 2-5 | Docker Compose 完整叢集 | 20-30 秒 |
> | 中型 | 6-15 | 混合 Mock (測試目標服務 + Mock 依賴) | 10-15 秒 |
> | 大型 | 16+ | K8s Test Cluster + Contract Testing | 1-2 分鐘 |
>
> **測試環境隔離與清理**:
> ```bash
> #!/bin/bash
> # scripts/test-env-lifecycle.sh
> 
> # 建立隔離測試環境
> create_test_env() {
>   TEST_ID="test-${CI_JOB_ID}"
>   docker-compose -f docker-compose.test.yml -p "${TEST_ID}" up -d
>   echo "Test environment created: ${TEST_ID}"
> }
> 
> # 執行測試
> run_tests() {
>   TEST_ID="test-${CI_JOB_ID}"
>   docker-compose -p "${TEST_ID}" exec -T test-runner npm test
> }
> 
> # 清理測試環境
> cleanup_test_env() {
>   TEST_ID="test-${CI_JOB_ID}"
>   docker-compose -p "${TEST_ID}" down -v  # -v 刪除 volumes
>   echo "Test environment cleaned: ${TEST_ID}"
> }
> 
> # 自動清理超過 1 小時的測試環境
> cleanup_stale_envs() {
>   # 跨平台寫法：`xargs -r`（無輸入不執行）為 GNU-only，BSD/macOS xargs 無 -r；
>   # while read 迴圈天然跳過空輸入，macOS/Linux 皆可原樣照抄
>   docker ps -a --filter "label=com.docker.compose.project=test-*" \
>     --filter "status=exited" --format "{{.ID}}" \
>     | while read -r id; do docker rm -v "$id"; done
> }
> ```

```

**📋 Test Environment as Code 最佳實踐** 🆕 (v0.01 新增)

> **核心原則**：測試環境應像程式碼一樣版本控制、可重現、可自動化。

**目錄結構建議**：
```
test-environments/
├── docker-compose.test.yml      # 本地測試環境
├── docker-compose.ci.yml        # CI 測試環境
├── terraform/                   # 雲端測試環境 (IaC)
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── fixtures/                    # 測試資料
│   ├── seed-data.sql
│   └── mock-data.json
└── scripts/
    ├── setup.sh                 # 環境設置腳本
    ├── teardown.sh              # 環境清理腳本
    └── health-check.sh          # 健康檢查腳本
```

**Test Environment as Code 檢查清單**：

| 檢查項目 | 說明 | 必要性 |
|---------|------|--------|
| **版本控制** | 環境配置在 Git 中管理 | 🔴 必要 |
| **可重現性** | 任何人可一鍵重建環境 | 🔴 必要 |
| **隔離性** | 測試環境與 Prod 完全隔離 | 🔴 必要 |
| **冪等性** | 重複執行 setup 結果一致 | 🔴 必要 |
| **自動清理** | 測試完自動釋放資源 | ⚠️ 建議 |
| **成本控制** | 測試環境有使用時間限制 | ⚠️ 建議 |

**Testcontainers 整合範例**：
```javascript
// 使用 Testcontainers 自動管理測試容器
const { GenericContainer } = require('testcontainers');

let postgresContainer;

beforeAll(async () => {
  postgresContainer = await new GenericContainer('postgres:15')
    .withExposedPorts(5432)
    .withEnvironment({ POSTGRES_PASSWORD: 'test' })
    .start();

  process.env.DATABASE_URL = `postgresql://postgres:test@${postgresContainer.getHost()}:${postgresContainer.getMappedPort(5432)}/postgres`;
});

afterAll(async () => {
  await postgresContainer.stop();
});
```

**環境一致性驗證**：
```bash
# 驗證測試環境與生產環境版本一致性
#!/bin/bash
check_version_consistency() {
  PROD_POSTGRES=$(kubectl get deployment -n prod -o jsonpath='{.spec.template.spec.containers[0].image}')
  # 跨平台寫法：`grep -oP`（PCRE 的 \K）為 GNU-only，BSD/macOS grep 無 -P；
  # 以 POSIX BRE 的 sed 等價擷取（head -1 確保多筆命中時輸出單一值）
  TEST_POSTGRES=$(sed -n 's/.*postgres:\([^"[:space:]]*\).*/\1/p' docker-compose.test.yml | head -1)

  if [[ "$PROD_POSTGRES" != "$TEST_POSTGRES" ]]; then
    echo "⚠️ 版本不一致: Prod=$PROD_POSTGRES, Test=$TEST_POSTGRES"
    exit 1
  fi
}
```

---

> 🔴 **人機協作點**: 測試環境管理確認
> - 確認測試環境隔離策略（避免環境衝突）
> - 驗證測試資料管理方案（資料生成/重置/清理）
> - 確認環境配置的一致性（Dev/Test/Prod）
> - 審查環境資源使用和成本控制

---

### 階段 5：測試報告與改進 (30 分鐘)

#### 步驟 5.1：測試報告生成

**測試覆蓋率報告**：
```json
// package.json
{
  "scripts": {
    "test": "jest --coverage --coverageReporters=text --coverageReporters=html"
  },
  "jest": {
    "coverageThreshold": {
      "global": {
        "branches": 75,
        "functions": 80,
        "lines": 80,
        "statements": 80
      }
    }
  }
}
```

**測試結果儀表板**：
- **工具**：Allure, ReportPortal
- **指標**：通過率、失敗率、跳過率、執行時間
- **趨勢**：測試覆蓋率趨勢、缺陷趨勢

**持續改進**：
- 定期檢視測試失敗原因
- 識別 Flaky Tests（不穩定測試）並修復
- 測試執行時間優化
- 測試覆蓋率提升

---

## 🎯 成功標準

### 測試覆蓋率
- [ ] 整體覆蓋率 ≥ 80%
- [ ] 關鍵業務邏輯 100%
- [ ] 分支覆蓋率 ≥ 75%

### 自動化程度
- [ ] 單元測試 100% 自動化
- [ ] 整合測試 ≥ 80% 自動化
- [ ] E2E 測試覆蓋關鍵流程

### 測試穩定性
- [ ] 測試通過率 ≥ 98%
- [ ] Flaky Tests < 2%
- [ ] 測試執行時間可接受

---

## 📊 時間分配參考

| 階段 | 預估時間 |
|------|---------|
| 啟動和情境確認 | 20 分鐘 |
| 測試策略制定 | 40-60 分鐘 |
| 測試案例設計 | 1-1.5 小時 |
| 測試自動化實施 | 1-1.5 小時 |
| 測試環境管理 | 30-40 分鐘 |
| 測試報告與改進 | 30 分鐘 |
| **準備階段總計** | **3-4 小時** |
| **實際開發時間** | 1-2 週 |

---

## 💡 最佳實踐

### 1. 測試金字塔平衡
- 60% 單元測試（快速、穩定）
- 30% 整合測試（驗證整合）
- 10% E2E 測試（驗證流程）

### 2. 測試獨立性
- 測試間不互相依賴
- 每個測試可單獨執行
- 測試資料獨立

### 3. 快速回饋
- 單元測試 < 10 秒
- 整合測試 < 2 分鐘
- E2E 測試 < 10 分鐘

### 4. 持續維護
- 定期清理無效測試
- 修復 Flaky Tests
- 更新測試案例

> 🔴 **人機協作點**: 測試報告與改進確認
> - 審查測試覆蓋率報告（是否達成目標 ≥ 80%）
> - 分析測試失敗模式和根本原因
> - 確認測試改進優先級和執行計畫
> - 驗證測試文檔的完整性和可維護性

---

### 階段 6：行動端與跨平台測試 (選擇性, 30-60 分鐘) 🆕 v0.01 補充

> **適用條件**: 專案包含 Android / iOS / macOS 原生或跨平台應用時啟用此階段。
> **自動載入**: 啟用時自動載入 `qa-mobile-tester-zh.yaml` Agent。

#### 步驟 6.1：行動端測試策略

**測試範圍識別**：

| 平台 | 測試框架 | 重點驗證項 |
|------|---------|-----------|
| **Android** | Espresso / Appium | UI 渲染、手勢操作、權限管理、後台行為 |
| **iOS** | XCUITest / Appium | UI 適配、推播通知、生物辨識、App Transport Security |
| **macOS** | XCUITest | 視窗管理、快捷鍵、Menu Bar 整合 |
| **跨平台 (Flutter/RN)** | Appium / Detox | 平台一致性、原生元件橋接 |

**裝置矩陣定義**：
```yaml
device_matrix:
  android:
    - { name: "Pixel 7", os: "Android 14", category: "flagship" }
    - { name: "Samsung A14", os: "Android 12", category: "mid-range" }
    - { name: "低階裝置模擬", ram: "2GB", category: "low-end" }
  ios:
    - { name: "iPhone 15", os: "iOS 17", category: "flagship" }
    - { name: "iPhone SE 3", os: "iOS 16", category: "compact" }
  macos:
    - { name: "MacBook Air M2", os: "macOS 14", category: "standard" }
```

#### 步驟 6.2：行動端專屬測試類型

**1. 條碼掃描功能測試**（經銷存等含掃碼功能的系統）：

| 測試場景 | 驗證重點 | 通過標準 |
|---------|---------|---------|
| 正常掃描 | QR Code / Barcode 辨識 | 辨識率 ≥ 99% |
| 低光環境 | 閃光燈自動開啟 + 辨識 | 可在 50 lux 以下正常掃描 |
| 模糊條碼 | 容錯辨識 | 破損 < 20% 仍可辨識 |
| 連續掃描 | 批量掃描效能 | ≥ 30 筆/分鐘 |
| 離線掃描 | 離線暫存 + 恢復上傳 | 網路恢復後 100% 同步 |

**2. 離線模式與資料同步**：

```
測試流程：
1. 正常連線 → 建立資料基準
2. 切斷網路 → 繼續操作（新增/修改/刪除）
3. 恢復網路 → 驗證同步結果
4. 衝突場景 → 驗證衝突解決策略
```

**3. App 生命週期測試**：
- 前景 → 背景 → 前景：狀態保持
- 記憶體不足強制關閉 → 重啟恢復
- 系統更新 / 權限變更後行為
- 推播通知觸發與深度連結

#### 步驟 6.3：行動端效能測試

**關鍵效能指標**：

| 指標 | Android 標準 | iOS 標準 | 測量工具 |
|------|------------|---------|---------|
| 冷啟動時間 | < 2s | < 1.5s | Android Profiler / Instruments |
| 記憶體占用 | < 150MB | < 120MB | LeakCanary / Xcode Memory Graph |
| CPU 使用率 | < 30% (閒置) | < 25% (閒置) | Systrace / Instruments |
| 電量消耗 | < 5%/hr (背景) | < 3%/hr (背景) | Battery Historian |
| 網路流量 | 首頁 < 500KB | 首頁 < 500KB | Charles Proxy |

#### 步驟 6.4：行動端測試自動化範例

**Appium (Android 掃碼測試)**：
```java
@Test
void testBarcodeScanAndSync() {
    // 開啟掃碼頁面
    driver.findElement(AppiumBy.id("btn_scan")).click();

    // 模擬掃描條碼（使用預製圖片注入相機）
    driver.pushFile("/sdcard/barcode_test.png", testBarcodeImage);
    driver.executeScript("mobile: shell", ImmutableMap.of(
        "command", "am broadcast -a com.test.SCAN_BARCODE --es code 'PRD-2024-001'"
    ));

    // 驗證掃描結果
    WebElement result = driver.findElement(AppiumBy.id("scan_result"));
    assertEquals("PRD-2024-001", result.getText());

    // 驗證資料同步至後端
    WebElement syncStatus = driver.findElement(AppiumBy.id("sync_status"));
    assertEquals("已同步", syncStatus.getText());
}
```

> 🔴 **人機協作點**: 行動端測試確認
> - 確認目標平台清單和裝置矩陣
> - 審查特殊場景（離線、掃碼、權限）覆蓋度
> - 驗證 App Store / Play Store 提交前合規檢查

---

## 📚 實際案例走查

> 💡 **學習價值**: 透過真實專案案例,了解測試策略的實際應用、常見挑戰與解決方案。

### 案例 1: 測試覆蓋率從 0% 到 80% - Legacy 專案測試補強

**專案背景**:
- **專案類型**: Web App (電商後端 API)
- **團隊規模**: 4 人 (1 QA Lead + 2 QA + 1 Dev)
- **技術棧**: Node.js, Express, PostgreSQL, Redis
- **代碼規模**: 約 15 萬行代碼
- **專案週期**: 3 個月
- **專案目標**: 將完全無測試的 Legacy 系統建立完整測試體系,達成 80% 覆蓋率

**執行過程** (依 SOP 階段):

#### 階段 1: 測試策略制定 (實際耗時: 3 天)
- ✅ **完成項目**:
  - 分析現有代碼,識別核心業務模組 (訂單、支付、庫存)
  - 制定測試金字塔策略: 單元測試 60% + 整合測試 30% + E2E 10%
  - 優先級排序: P0 核心業務 → P1 次要功能 → P2 邊緣功能
- ⚠️ **遇到問題**: 代碼耦合嚴重,難以單元測試
- 💡 **解決方案**: 先用 Golden Master Testing (特徵測試) 建立安全網,再逐步重構
- 📊 **階段產出**: 測試策略文件、優先級矩陣、3 個月測試路線圖

#### 階段 2: 測試基礎建立 (實際耗時: 1 週)
- ✅ **完成項目**:
  - 選定測試框架: Jest (單元+整合) + Supertest (API) + Playwright (E2E)
  - 建立 CI/CD 整合: GitHub Actions 自動執行測試
  - 建立測試環境: Testcontainers (Docker 化 PostgreSQL + Redis)
- ⚠️ **遇到問題**: CI 執行時間過長 (初期 20 分鐘)
- 💡 **解決方案**: 使用 Jest 並行執行 + 快取依賴,優化至 5 分鐘
- 📊 **階段產出**: 測試基礎設施、CI/CD Pipeline、測試腳本模板

#### 階段 3-4: 測試撰寫與執行 (實際耗時: 10 週)
- ✅ **完成項目**:
  - 第 1-4 週: Golden Master Testing (核心 API 端點)
  - 第 5-8 週: 單元測試補強 (business logic 層)
  - 第 9-10 週: E2E 測試 (關鍵使用者流程)
  - 建立測試資料生成器 (Faker.js + TestDataFactory)
- ⚠️ **遇到問題**: Flaky Tests (不穩定測試) 頻繁失敗
- 💡 **解決方案**:
  - 使用 `test.retry(3)` 自動重試
  - 增加明確的等待條件 (`waitForSelector`)
  - 避免依賴絕對時間 (改用相對時間)
- 📊 **階段產出**:
  - 單元測試: 856 個 (覆蓋率 62%)
  - 整合測試: 142 個 (覆蓋率 28%)
  - E2E 測試: 18 個關鍵流程

**關鍵經驗**:
- 💡 **成功經驗 1**: Golden Master Testing 快速建立安全網,避免回歸錯誤
- 💡 **成功經驗 2**: Testcontainers 確保測試環境一致性,消除「本地可以跑,CI 失敗」問題
- 💡 **成功經驗 3**: 測試優先級排序,先保護核心業務邏輯
- ⚠️ **避坑指南 1**: 不要追求 100% 覆蓋率,80% 是性價比最高的目標
- ⚠️ **避坑指南 2**: Legacy 代碼難以測試時,先用 Golden Master 而非強行重構
- ⚠️ **避坑指南 3**: Flaky Tests 要立即修復,不能累積
- 🔄 **流程調整**: 原訂「先重構再測試」調整為「先 Golden Master 建立安全網,再邊重構邊補單元測試」

**量化成果**:
- **測試覆蓋率**: 從 0% 提升至 82% (超過目標 80%)
- **Bug 發現率**: 測試期間發現 47 個潛在 Bug (未上線前修復)
- **迴歸錯誤**: 從每次部署 2-3 個降至 0.2 個 (90% 減少)
- **部署信心**: 團隊部署信心從 3/10 提升至 9/10
- **CI 執行時間**: 5 分鐘 (可接受範圍)
- **維護成本**: 測試維護時間約佔開發時間 15% (合理)

---

### 案例 2: E2E 自動化測試建立 - 手動測試轉自動化

**專案背景**:
- **專案類型**: Web App (B2B SaaS 專案管理工具)
- **團隊規模**: 3 人 (1 QA Lead + 2 QA)
- **技術棧**: React, TypeScript, Playwright
- **專案週期**: 6 週
- **專案目標**: 將手動測試 (每次發版 8 小時) 轉為自動化 E2E 測試

**執行過程摘要**:

#### 階段 1-2: 策略與框架選擇 (5 天)
- ✅ **成功**: 選定 Playwright (支援多瀏覽器、錄製功能、平行執行)
- ⚠️ **挑戰**: 團隊對 Playwright 不熟悉
- 💡 **解決**: 投入 2 天集體學習 + 建立 POC
- 📊 **產出**: 測試策略文件、框架選型 ADR

#### 階段 3-4: 測試撰寫與優化 (4 週)
- ✅ **成功**:
  - 建立 Page Object Model 提升可維護性
  - 使用 Playwright Codegen 快速錄製測試
  - 建立 32 個關鍵使用者流程的 E2E 測試
- ⚠️ **挑戰**: 測試執行時間過長 (45 分鐘)
- 💡 **解決**:
  - 並行執行 (從串行改為 4 個 worker 並行)
  - 優化等待策略 (避免 `sleep`,改用智能等待)
  - 執行時間優化至 12 分鐘
- 📊 **產出**: 32 個 E2E 測試、測試報告儀表板 (Allure)

**關鍵經驗**:
- 💡 **成功經驗**: Page Object Model 讓測試易於維護,UI 變更時只需修改 Page Object
- ⚠️ **避坑指南**: 避免測試間相互依賴,每個測試應獨立可執行
- 🔄 **流程調整**: 從「錄製測試後直接使用」調整為「錄製 → 重構為 Page Object → 優化等待」

**量化成果**:
- **測試執行時間**: 從 8 小時 (手動) → 12 分鐘 (自動化),效率提升 **40 倍**
- **測試覆蓋**: 32 個關鍵使用者流程 100% 自動化
- **發現 Bug**: 自動化測試發現 11 個手動測試遺漏的邊緣案例
- **迴歸測試**: 每次 PR 自動執行,迴歸錯誤降低 95%
- **團隊滿意度**: QA 滿意度從 5/10 提升至 9/10 (不再需要重複手動測試)
- **ROI**: 3 個月收回投資成本 (節省的手動測試時間)

---

## 🎓 相關資源

- [Testing SOP 完整版](./SOP.md)
- [Testing DeepDive 深度指南](./SOP_DeepDive.md)
- [Testing QuickRef 快速參考](./SOP_QuickRef.md)
- [Testing 快速啟動指令集](../../prompts/scenario-prompts/testing-prompts.md)
- [testing-strategy-flow Workflow](../../workflow/scenario-specific/testing-strategy-flow.md)
- [AISDLC_INIT.md](../../AISDLC_INIT.md)

### 相關 Agents
- [qa-lead-zh.yaml](../../agent/specialized/qa-lead-zh.yaml) - QA Lead（主導：測試策略制定）
- [qa-automation-zh.yaml](../../agent/specialized/qa-automation-zh.yaml) - QA Automation（自動化測試設計）
- [dev-developer-zh.yaml](../../agent/core/06.dev-developer-zh.yaml) - David（測試實作支援）
- [qa-tester-zh.yaml](../../agent/core/07.qa-tester-zh.yaml) - Quincy（驗收測試與品質驗證）
- [qa-web-tester-zh.yaml](../../agent/specialized/qa-web-tester-zh.yaml) - Web QA（Web 前端測試，選用）
- [qa-mobile-tester-zh.yaml](../../agent/specialized/qa-mobile-tester-zh.yaml) - Mobile QA（行動端測試，選用）
- [security-engineer-zh.yaml](../../agent/specialized/security-engineer-zh.yaml) - Security Engineer（安全測試，選用）
- [performance-engineer-zh.yaml](../../agent/specialized/performance-engineer-zh.yaml) - Performance Engineer（效能/負載測試，選用）
- [devops-engineer-zh.yaml](../../agent/specialized/devops-engineer-zh.yaml) - DevOps Engineer（測試環境與 CI/CD 整合，選用）
- [integration-specialist-zh.yaml](../../agent/specialized/integration-specialist-zh.yaml) - Integration Specialist（跨模組整合測試、第三方 API 契約驗證、QR Code 掃碼整合，選用）

---

## 🔐 電商/訂閱/付費內容系統強制安全測試項（v0.01 新增）

> **⚠️ 適用條件**：系統含電商金流、付費內容（付費牆）、訂閱方案、民宿預訂支付時，**必須**在階段 2 中額外執行以下測試。

### 強制測試項 A：付費內容 API 授權

| 測試 ID | 測試描述 | 驗證重點 | 失敗影響 |
|---------|---------|---------|---------|
| **PAID-001** | 未登入直接呼叫付費內容 API | 應回傳 401 | 🔴 Critical — 內容全面外洩 |
| **PAID-002** | 已登入但未訂閱用戶呼叫付費 API | 應回傳 403 | 🔴 Critical — 付費牆形同虛設 |
| **PAID-003** | 訂閱到期後呼叫付費 API | 應回傳 403（需 Scheduler 定時降權）| 🔴 Critical — 訂閱計費失效 |
| **PAID-004** | 繞過前端付費牆直接 curl API | 應回傳 403 | 🔴 Critical — 前端限制≠後端授權 |

> **Spring Boot 驗證方式**：`@PreAuthorize("hasAuthority('SUBSCRIPTION_ACTIVE')")` 或自訂 `AccessDeniedHandler`

### 強制測試項 B：Server-side 金額驗算

| 測試 ID | 測試描述 | 驗證重點 | 失敗影響 |
|---------|---------|---------|---------|
| **PRICE-001** | 篡改 POST body 中的金額後送出訂單 | 後端應用商品價格重算，拒絕異常金額 | 🔴 Critical — 1 元購買任意商品 |
| **PRICE-002** | 優惠券折扣疊加超過商品價格 | 最終金額不得為負數 | 🔴 Critical — 負數付款 |
| **PRICE-003** | 金流 Webhook 重複回調同一筆交易 | 冪等性驗證（Idempotency Key）| 🔴 Critical — 重複解鎖/重複發貨 |
| **PRICE-004** | 金流 Webhook HMAC 簽名驗證 | 拒絕無效簽名 Webhook | 🔴 Critical — 假冒支付成功 |

### 強制測試項 C：並發安全（Race Condition）

| 測試 ID | 測試描述 | 驗證重點 | 失敗影響 |
|---------|---------|---------|---------|
| **RACE-001** | 同一商品最後 1 件，10 個並發請求同時下單 | 僅 1 筆成立，庫存不得為負 | 🔴 Critical — 超賣 |
| **RACE-002** | 同一民宿房間相同日期，5 個並發訂房 | 僅 1 筆成立，不可雙重訂房 | 🔴 Critical — 雙重訂房 |
| **RACE-003** | QR Code Check-in 重複掃描（並發 3 次）| 僅 1 次 Check-in 成立 | 🔴 High — 記錄異常 |

> **Spring Boot 建議方案**：
> - 庫存/訂房：`SELECT ... FOR UPDATE`（悲觀鎖）或 `@Version`（樂觀鎖 + 重試）
> - QR Code：Redis `SET NX EX`（原子性一次性 Token）
> - k6 並發測試腳本（`executor: shared-iterations`）模擬並發場景

---

### 相關 Skills
- `/testing-strategy` - 測試策略設計、測試金字塔建立
- `/qa-testing` - 測試計畫、驗收測試、測試案例撰寫
- `/security-audit` - 安全測試（OWASP Top 10、SAST/DAST）
- `/performance-optimization` - 效能基準測試、負載測試
- `/devops-github-actions` - GitHub Actions CI 測試整合
- `/devops-gitlab-ci` - GitLab CI 測試整合
- `/devops-docker` - Docker 測試環境建置
- `/devops-monitoring` - 測試指標監控與儀表板
- `/code-review` - 程式碼審查與測試品質
- `/integration-database` - 資料庫測試（PostgreSQL）
- `/mobile-development` - 行動端測試（涉及 Android/iOS/macOS 時）

---

**下一步**：準備好專案後，執行 [階段 1](#階段-1測試策略制定-40-60-分鐘) 開始建立完整測試體系！

---

## AutoClaude 自動化執行（Phase Z / v0.02 新增）

> 規格凍結（SPEC_FROZEN）後，本場景以 Contract 覆蓋驅動的 AT 契約可交由 AutoClaude 引擎全自動執行實作與雙重驗證。
> 標準作業全文：`workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md`；
> 翻譯保真規則：`governance/rules/R-9.38-playbook-translation-fidelity.yaml`。

1. **編譯**（AutoClaude/ 目錄）：`python -m autoclaude.tools.sdd_compile --spec-dir <docs path> --out playbooks/sdd_bridge.yaml`
   - 規格未凍結 → exit 2 拒絕（Spec-First 硬閘）；weak_regex 斷言入 audit log。
2. **人工 review** 生成的 playbook YAML（SCG-4 精神：生成物 = 待審工件）。
3. **執行**：`python -m autoclaude playbooks/sdd_bridge.yaml` — SddGovernancePlugin 自動守 SCG 閘門、記帳契約違反、防規格 drift。
4. 🔴 人工確認閘門不可由自動化跳過（Rule 8）；ESCALATION 後必等人工。
