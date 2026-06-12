---
name: testing
description: 設計測試策略，建立測試金字塔，撰寫測試案例
user-invocable: true
disable-model-invocation: false
argument-hint: "[framework: 測試框架 (jest/vitest/pytest/junit)] [scope: 測試範圍 (unit/integration/e2e/full)]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
  - Bash
---

# Testing Strategy Skill

基於 AISDLC Testing 情境的測試策略技能。

---

## 觸發方式

```bash
/testing                    # 完整測試策略
/testing unit jest          # Jest 單元測試
/testing e2e cypress        # E2E 測試
/testing --scope=full       # 全面測試規劃
```

---

## 執行流程

### 階段 1: 測試評估 (10分鐘)

**現況分析**:
```bash
# 檢查現有測試
npm test -- --coverage --json > coverage.json

# 分析覆蓋率
npx jest --coverage --coverageReporters="text-summary"
```

**測試金字塔檢查**:
```
        △ E2E Tests (10%)
       ╱ ╲  - 關鍵用戶流程
      ╱   ╲ - 耗時但高信心
     ╱─────╲
    ╱ Integration (20%) ╲
   ╱   - API 測試         ╲
  ╱    - 元件整合測試      ╲
 ╱─────────────────────────╲
╱    Unit Tests (70%)       ╲
- 函數測試、工具測試
- 快速、隔離、大量
```

🔴 **確認點**: 確認測試重點和優先級

---

### 階段 2: 測試案例設計

#### 單元測試範例 (Jest/Vitest)

```typescript
// src/utils/calculator.test.ts
import { describe, it, expect } from 'vitest';
import { calculateDiscount } from './calculator';

describe('calculateDiscount', () => {
  describe('when amount is below threshold', () => {
    it('should return 0 discount', () => {
      expect(calculateDiscount(50)).toBe(0);
    });
  });

  describe('when amount is above threshold', () => {
    it('should apply 10% discount', () => {
      expect(calculateDiscount(150)).toBe(15);
    });
  });

  describe('edge cases', () => {
    it('should handle zero amount', () => {
      expect(calculateDiscount(0)).toBe(0);
    });

    it('should handle negative amount', () => {
      expect(() => calculateDiscount(-10)).toThrow('Invalid amount');
    });
  });
});
```

#### 整合測試範例

```typescript
// src/api/users.test.ts
import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { createServer } from '../server';
import request from 'supertest';

describe('Users API', () => {
  let app: Express;

  beforeAll(async () => {
    app = await createServer();
  });

  describe('GET /api/users', () => {
    it('should return list of users', async () => {
      const response = await request(app)
        .get('/api/users')
        .expect(200);

      expect(response.body).toHaveProperty('users');
      expect(Array.isArray(response.body.users)).toBe(true);
    });
  });

  describe('POST /api/users', () => {
    it('should create a new user', async () => {
      const response = await request(app)
        .post('/api/users')
        .send({ name: 'John', email: 'john@example.com' })
        .expect(201);

      expect(response.body).toHaveProperty('id');
    });

    it('should reject invalid email', async () => {
      await request(app)
        .post('/api/users')
        .send({ name: 'John', email: 'invalid' })
        .expect(400);
    });
  });
});
```

#### E2E 測試範例 (Playwright)

```typescript
// e2e/login.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Login Flow', () => {
  test('should login successfully', async ({ page }) => {
    await page.goto('/login');

    await page.fill('[data-testid="email"]', 'user@example.com');
    await page.fill('[data-testid="password"]', 'password123');
    await page.click('[data-testid="submit"]');

    await expect(page).toHaveURL('/dashboard');
    await expect(page.locator('[data-testid="welcome"]')).toContainText('Welcome');
  });

  test('should show error for invalid credentials', async ({ page }) => {
    await page.goto('/login');

    await page.fill('[data-testid="email"]', 'wrong@example.com');
    await page.fill('[data-testid="password"]', 'wrongpass');
    await page.click('[data-testid="submit"]');

    await expect(page.locator('[data-testid="error"]')).toBeVisible();
  });
});
```

---

### 階段 3: 測試配置

**Jest 配置**:
```javascript
// jest.config.js
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  coverageThreshold: {
    global: {
      branches: 70,
      functions: 70,
      lines: 70,
      statements: 70,
    },
  },
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/*.test.ts',
  ],
};
```

**Playwright 配置**:
```typescript
// playwright.config.ts
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 30000,
  retries: 2,
  use: {
    baseURL: 'http://localhost:3000',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
});
```

---

### 階段 4: CI 整合

**GitHub Actions 測試工作流**:
```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: npm ci
      - run: npm run lint
      - run: npm test -- --coverage

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## 產出物

| 產出物 | 說明 |
|--------|------|
| 測試策略文檔 | 測試方法和覆蓋目標 |
| 測試案例 | 具體測試代碼 |
| 測試配置 | 框架配置檔案 |
| CI 整合 | 自動化測試流程 |

---


## 相關檔案

- SOP 參考: `scenarios/testing/SOP_QuickRef.md`

**基於**: AISDLC v0.09 Testing 情境
