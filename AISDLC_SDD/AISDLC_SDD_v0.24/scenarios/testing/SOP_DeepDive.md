# Testing 測試策略與實踐 - 深度技術指南
# Deep Dive Technical Guide

**版本**: v0.01
**最後更新**: 2025-10-29
**適用對象**: 經驗豐富的測試工程師、QA 主管、測試架構師
**建議閱讀**: 先閱讀 SOP_QuickRef.md 和 SOP.md
**文檔類型**: 技術參考、最佳實踐、深度分析

---

## 📚 文檔說明

### 何時閱讀此文檔

✅ **適合閱讀的情況**:
- 建立完整的測試策略和測試金字塔
- 實施測試自動化框架
- 處理複雜的端到端測試場景
- 設計測試資料管理策略
- 實施持續測試和測試左移
- 優化測試執行效率

❌ **不建議閱讀的情況**:
- 初次編寫測試(請閱讀 SOP.md)
- 快速參考測試步驟(請閱讀 SOP_QuickRef.md)
- 簡單的單元測試

### 文檔結構

```
Part 1: 測試策略與測試金字塔
Part 2: 單元測試深度實踐
Part 3: 整合測試策略
Part 4: 端到端測試自動化
Part 5: 效能測試與負載測試
Part 6: 安全測試
Part 7: 測試資料管理
Part 8: 測試環境管理
Part 9: 測試度量與報告
Part 10: 真實案例研究
```

---

## Part 1: 測試策略與測試金字塔

### 1.1 測試金字塔進階

```yaml
測試金字塔結構:

Level 4: E2E Tests (端到端測試) - 5%
  - 關鍵用戶流程
  - 跨系統整合
  - UI 自動化測試
  成本: 高 | 速度: 慢 | 維護: 困難

Level 3: Integration Tests (整合測試) - 20%
  - API 測試
  - 資料庫整合
  - 外部服務整合
  成本: 中 | 速度: 中 | 維護: 中等

Level 2: Component Tests (元件測試) - 30%
  - React/Vue 元件測試
  - 服務層測試
  - 模組測試
  成本: 低 | 速度: 快 | 維護: 容易

Level 1: Unit Tests (單元測試) - 45%
  - 函數級測試
  - 類別測試
  - 純邏輯測試
  成本: 極低 | 速度: 極快 | 維護: 極容易

最佳實踐比例: 70% Unit, 20% Integration, 10% E2E
```

### 1.2 測試優先級矩陣

```yaml
優先級判斷標準:

High Priority (P0):
  - 核心業務流程
  - 支付相關功能
  - 認證授權
  - 資料完整性

Medium Priority (P1):
  - 常用功能
  - 資料驗證
  - 錯誤處理

Low Priority (P2):
  - 邊緣情況
  - UI 細節
  - 非關鍵功能
```

---

## Part 2: 單元測試深度實踐

### 2.1 測試驅動開發 (TDD)

**紅-綠-重構循環**:

```javascript
// ===== Step 1: Red - 寫一個失敗的測試 =====

describe('OrderService', () => {
  describe('calculateTotal', () => {
    it('should calculate total with tax', () => {
      const order = {
        items: [
          { price: 100, quantity: 2 },
          { price: 50, quantity: 1 }
        ],
        taxRate: 0.1
      };

      const total = OrderService.calculateTotal(order);

      expect(total).toBe(275); // 250 + 25 (10% tax)
    });
  });
});

// 執行測試 → ❌ 失敗 (函數不存在)

// ===== Step 2: Green - 寫最簡單能通過的代碼 =====

class OrderService {
  static calculateTotal(order) {
    const subtotal = order.items.reduce((sum, item) => {
      return sum + (item.price * item.quantity);
    }, 0);

    const tax = subtotal * order.taxRate;
    return subtotal + tax;
  }
}

// 執行測試 → ✅ 通過

// ===== Step 3: Refactor - 重構代碼 =====

class OrderService {
  static calculateTotal(order) {
    const subtotal = this.calculateSubtotal(order.items);
    const tax = this.calculateTax(subtotal, order.taxRate);
    return subtotal + tax;
  }

  static calculateSubtotal(items) {
    return items.reduce((sum, item) => {
      return sum + (item.price * item.quantity);
    }, 0);
  }

  static calculateTax(amount, rate) {
    return amount * rate;
  }
}

// 執行測試 → ✅ 仍然通過

// ===== Step 4: 添加更多測試用例 =====

describe('OrderService', () => {
  describe('calculateTotal', () => {
    it('should calculate total with tax', () => {
      const order = {
        items: [{ price: 100, quantity: 2 }],
        taxRate: 0.1
      };
      expect(OrderService.calculateTotal(order)).toBe(220);
    });

    it('should handle zero tax rate', () => {
      const order = {
        items: [{ price: 100, quantity: 2 }],
        taxRate: 0
      };
      expect(OrderService.calculateTotal(order)).toBe(200);
    });

    it('should handle empty items', () => {
      const order = {
        items: [],
        taxRate: 0.1
      };
      expect(OrderService.calculateTotal(order)).toBe(0);
    });

    it('should handle discount', () => {
      const order = {
        items: [{ price: 100, quantity: 2 }],
        taxRate: 0.1,
        discount: 20
      };
      // 需求變更 - 折扣後再計算稅
      expect(OrderService.calculateTotal(order)).toBe(198); // (200-20) * 1.1
    });
  });
});

// 最後一個測試失敗 → 需要實作 discount 功能
// 重複 TDD 循環...
```

### 2.2 測試替身 (Test Doubles)

**Stub, Mock, Spy 詳解**:

```javascript
// ===== Stub (樁) - 提供預設回應 =====

class UserService {
  constructor(userRepository) {
    this.userRepository = userRepository;
  }

  async getUser(id) {
    return await this.userRepository.findById(id);
  }
}

// 測試
describe('UserService', () => {
  it('should return user from repository', async () => {
    // 建立 stub
    const userRepositoryStub = {
      findById: jest.fn().mockResolvedValue({
        id: '123',
        name: 'John Doe'
      })
    };

    const service = new UserService(userRepositoryStub);
    const user = await service.getUser('123');

    expect(user.name).toBe('John Doe');
  });
});

// ===== Mock (模擬) - 驗證行為 =====

describe('UserService', () => {
  it('should call repository with correct id', async () => {
    const userRepositoryMock = {
      findById: jest.fn().mockResolvedValue({ id: '123' })
    };

    const service = new UserService(userRepositoryMock);
    await service.getUser('123');

    // 驗證調用
    expect(userRepositoryMock.findById).toHaveBeenCalledWith('123');
    expect(userRepositoryMock.findById).toHaveBeenCalledTimes(1);
  });
});

// ===== Spy (間諜) - 包裝真實對象 =====

describe('UserService', () => {
  it('should cache user after first fetch', async () => {
    const realRepository = new UserRepository();
    const spy = jest.spyOn(realRepository, 'findById');

    const service = new CachingUserService(realRepository);

    // 第一次調用
    await service.getUser('123');
    expect(spy).toHaveBeenCalledTimes(1);

    // 第二次調用 (應該從快取取得)
    await service.getUser('123');
    expect(spy).toHaveBeenCalledTimes(1); // 仍然只調用一次
  });
});

// ===== Fake (假物件) - 簡化實作 =====

class FakeUserRepository {
  constructor() {
    this.users = new Map();
  }

  async findById(id) {
    return this.users.get(id);
  }

  async create(user) {
    this.users.set(user.id, user);
    return user;
  }
}

describe('UserService with Fake', () => {
  it('should store and retrieve user', async () => {
    const fakeRepo = new FakeUserRepository();
    const service = new UserService(fakeRepo);

    await fakeRepo.create({ id: '123', name: 'John' });
    const user = await service.getUser('123');

    expect(user.name).toBe('John');
  });
});
```

---

## Part 3: 整合測試策略

### 3.1 API 整合測試

```javascript
// 使用 Supertest + Jest

const request = require('supertest');
const app = require('../src/app');
const db = require('../src/database');

describe('User API Integration Tests', () => {
  // Setup and Teardown
  beforeAll(async () => {
    await db.connect();
    await db.migrate.latest();
  });

  afterAll(async () => {
    await db.destroy();
  });

  beforeEach(async () => {
    await db('users').truncate();
  });

  describe('POST /api/users', () => {
    it('should create a new user', async () => {
      const userData = {
        name: 'John Doe',
        email: 'john@example.com',
        password: 'SecurePass123'
      };

      const response = await request(app)
        .post('/api/users')
        .send(userData)
        .expect(201)
        .expect('Content-Type', /json/);

      expect(response.body).toMatchObject({
        id: expect.any(String),
        name: userData.name,
        email: userData.email
      });

      expect(response.body.password).toBeUndefined(); // 不應該回傳密碼

      // 驗證資料庫
      const user = await db('users').where({ email: userData.email }).first();
      expect(user).toBeTruthy();
      expect(user.password).not.toBe(userData.password); // 密碼應該被雜湊
    });

    it('should reject duplicate email', async () => {
      // 先建立一個使用者
      await db('users').insert({
        name: 'Existing User',
        email: 'john@example.com',
        password: 'hashed'
      });

      const response = await request(app)
        .post('/api/users')
        .send({
          name: 'New User',
          email: 'john@example.com',
          password: 'SecurePass123'
        })
        .expect(409); // Conflict

      expect(response.body.error).toContain('already exists');
    });

    it('should validate email format', async () => {
      const response = await request(app)
        .post('/api/users')
        .send({
          name: 'John Doe',
          email: 'invalid-email',
          password: 'SecurePass123'
        })
        .expect(400);

      expect(response.body.errors).toContainEqual({
        field: 'email',
        message: 'Invalid email format'
      });
    });
  });

  describe('GET /api/users/:id', () => {
    it('should return user by id', async () => {
      // 準備測試資料
      const [userId] = await db('users').insert({
        name: 'John Doe',
        email: 'john@example.com',
        password: 'hashed'
      }).returning('id');

      const response = await request(app)
        .get(`/api/users/${userId}`)
        .expect(200);

      expect(response.body).toMatchObject({
        id: userId,
        name: 'John Doe',
        email: 'john@example.com'
      });
    });

    it('should return 404 for non-existent user', async () => {
      const response = await request(app)
        .get('/api/users/99999')
        .expect(404);

      expect(response.body.error).toContain('not found');
    });
  });

  describe('PUT /api/users/:id', () => {
    it('should update user', async () => {
      const [userId] = await db('users').insert({
        name: 'John Doe',
        email: 'john@example.com',
        password: 'hashed'
      }).returning('id');

      const response = await request(app)
        .put(`/api/users/${userId}`)
        .send({
          name: 'Jane Doe'
        })
        .set('Authorization', `Bearer ${await getAuthToken(userId)}`)
        .expect(200);

      expect(response.body.name).toBe('Jane Doe');

      // 驗證資料庫
      const user = await db('users').where({ id: userId }).first();
      expect(user.name).toBe('Jane Doe');
    });

    it('should require authentication', async () => {
      await request(app)
        .put('/api/users/123')
        .send({ name: 'New Name' })
        .expect(401);
    });
  });
});
```

### 3.2 資料庫整合測試

```python
# Python + pytest + SQLAlchemy

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, User, Order
from app.services import OrderService

@pytest.fixture(scope='function')
def db_session():
    """每個測試使用獨立的資料庫 session"""
    engine = create_engine('postgresql://user:pass@localhost/test_db')
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
    Base.metadata.drop_all(engine)

@pytest.fixture
def sample_user(db_session):
    """建立測試使用者"""
    user = User(
        name='John Doe',
        email='john@example.com'
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

class TestOrderService:
    def test_create_order(self, db_session, sample_user):
        """測試建立訂單"""
        service = OrderService(db_session)

        order = service.create_order(
            user_id=sample_user.id,
            items=[
                {'product_id': 1, 'quantity': 2, 'price': 100},
                {'product_id': 2, 'quantity': 1, 'price': 50}
            ]
        )

        assert order.id is not None
        assert order.user_id == sample_user.id
        assert order.total == 250
        assert len(order.items) == 2

        # 驗證資料庫
        db_order = db_session.query(Order).filter_by(id=order.id).first()
        assert db_order is not None
        assert db_order.total == 250

    def test_create_order_with_invalid_user(self, db_session):
        """測試使用無效用戶建立訂單"""
        service = OrderService(db_session)

        with pytest.raises(ValueError, match="User not found"):
            service.create_order(
                user_id=99999,
                items=[{'product_id': 1, 'quantity': 1, 'price': 100}]
            )

    def test_order_transaction_rollback(self, db_session, sample_user):
        """測試交易回滾"""
        service = OrderService(db_session)

        # 模擬失敗情況 (庫存不足)
        with pytest.raises(Exception, match="Insufficient stock"):
            service.create_order(
                user_id=sample_user.id,
                items=[{'product_id': 1, 'quantity': 99999, 'price': 100}]
            )

        # 驗證沒有建立訂單 (交易已回滾)
        orders = db_session.query(Order).filter_by(user_id=sample_user.id).all()
        assert len(orders) == 0
```

---

## Part 4: 端到端測試自動化

### 4.1 Playwright E2E 測試

```javascript
// tests/e2e/checkout.spec.js

const { test, expect } = require('@playwright/test');

test.describe('Checkout Flow', () => {
  test.beforeEach(async ({ page }) => {
    // 每個測試前重置資料庫
    await page.request.post('/api/test/reset-db');

    // 建立測試資料
    await page.request.post('/api/test/seed-data', {
      data: {
        users: [{ id: 1, email: 'test@example.com', password: 'password123' }],
        products: [
          { id: 1, name: 'Product 1', price: 100, stock: 10 },
          { id: 2, name: 'Product 2', price: 200, stock: 5 }
        ]
      }
    });
  });

  test('should complete full checkout process', async ({ page }) => {
    // Step 1: 登入
    await page.goto('/login');
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');

    await expect(page).toHaveURL('/dashboard');

    // Step 2: 瀏覽商品
    await page.goto('/products');
    await expect(page.locator('h1')).toContainText('Products');

    // Step 3: 添加商品到購物車
    await page.click('[data-testid="product-1"] button[aria-label="Add to cart"]');
    await page.click('[data-testid="product-2"] button[aria-label="Add to cart"]');

    // 驗證購物車徽章
    const cartBadge = page.locator('[data-testid="cart-badge"]');
    await expect(cartBadge).toHaveText('2');

    // Step 4: 查看購物車
    await page.click('[data-testid="cart-button"]');
    await expect(page).toHaveURL('/cart');

    // 驗證商品列表
    const cartItems = page.locator('[data-testid="cart-item"]');
    await expect(cartItems).toHaveCount(2);

    // 驗證總金額
    const total = page.locator('[data-testid="cart-total"]');
    await expect(total).toContainText('$300');

    // Step 5: 結帳
    await page.click('button:has-text("Proceed to Checkout")');
    await expect(page).toHaveURL('/checkout');

    // 填寫配送資訊
    await page.fill('input[name="address"]', '123 Main St');
    await page.fill('input[name="city"]', 'New York');
    await page.fill('input[name="zipCode"]', '10001');

    // 選擇付款方式
    await page.click('input[value="credit_card"]');
    await page.fill('input[name="cardNumber"]', '4111111111111111');
    await page.fill('input[name="cvv"]', '123');
    await page.selectOption('select[name="expiryMonth"]', '12');
    await page.selectOption('select[name="expiryYear"]', '2025');

    // Step 6: 確認訂單
    await page.click('button:has-text("Place Order")');

    // 等待訂單確認頁面
    await expect(page).toHaveURL(/\/order\/\d+/);
    await expect(page.locator('h1')).toContainText('Order Confirmed');

    // 驗證訂單詳情
    const orderNumber = await page.locator('[data-testid="order-number"]').textContent();
    expect(orderNumber).toMatch(/ORD-\d+/);

    await expect(page.locator('[data-testid="order-total"]')).toContainText('$300');

    // Step 7: 驗證電子郵件通知 (使用 MailHog 或 mock)
    const emails = await page.request.get('/api/test/emails');
    const emailData = await emails.json();

    expect(emailData).toContainEqual(
      expect.objectContaining({
        to: 'test@example.com',
        subject: expect.stringContaining('Order Confirmed'),
        body: expect.stringContaining(orderNumber)
      })
    );
  });

  test('should handle out of stock products', async ({ page }) => {
    // 將產品庫存設為 0
    await page.request.patch('/api/products/1', {
      data: { stock: 0 }
    });

    await page.goto('/products');
    await page.click('[data-testid="product-1"] button[aria-label="Add to cart"]');

    // 應該顯示錯誤訊息
    const toast = page.locator('[role="alert"]');
    await expect(toast).toContainText('Out of stock');

    // 購物車應該是空的
    const cartBadge = page.locator('[data-testid="cart-badge"]');
    await expect(cartBadge).not.toBeVisible();
  });

  test('should validate payment information', async ({ page }) => {
    // ... 登入和添加商品到購物車的步驟 ...

    await page.goto('/checkout');

    // 填寫無效的信用卡號
    await page.fill('input[name="cardNumber"]', '1234');
    await page.click('button:has-text("Place Order")');

    // 應該顯示驗證錯誤
    const error = page.locator('text=Invalid credit card number');
    await expect(error).toBeVisible();
  });
});

// 使用 Page Object Model 重構

class LoginPage {
  constructor(page) {
    this.page = page;
    this.emailInput = page.locator('input[name="email"]');
    this.passwordInput = page.locator('input[name="password"]');
    this.submitButton = page.locator('button[type="submit"]');
  }

  async goto() {
    await this.page.goto('/login');
  }

  async login(email, password) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
  }
}

class ProductsPage {
  constructor(page) {
    this.page = page;
  }

  async addToCart(productId) {
    await this.page.click(`[data-testid="product-${productId}"] button[aria-label="Add to cart"]`);
  }

  async getCartBadgeCount() {
    return await this.page.locator('[data-testid="cart-badge"]').textContent();
  }
}

// 使用 Page Objects
test('checkout flow with page objects', async ({ page }) => {
  const loginPage = new LoginPage(page);
  const productsPage = new ProductsPage(page);

  await loginPage.goto();
  await loginPage.login('test@example.com', 'password123');

  await productsPage.addToCart(1);
  const count = await productsPage.getCartBadgeCount();
  expect(count).toBe('1');
});
```

---

## Part 5: 效能測試與負載測試

### 5.1 K6 負載測試

```javascript
// load-test.js

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// 自訂指標
const errorRate = new Rate('errors');
const checkoutDuration = new Trend('checkout_duration');

// 測試配置
export const options = {
  stages: [
    { duration: '2m', target: 100 },   // Ramp up to 100 users
    { duration: '5m', target: 100 },   // Stay at 100 users
    { duration: '2m', target: 200 },   // Ramp up to 200 users
    { duration: '5m', target: 200 },   // Stay at 200 users
    { duration: '2m', target: 0 },     // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% 的請求應在 500ms 內
    errors: ['rate<0.1'],              // 錯誤率應低於 10%
  },
};

// 測試資料
const users = JSON.parse(open('./test-data/users.json'));

export default function () {
  const user = users[Math.floor(Math.random() * users.length)];

  // Scenario 1: 登入
  let loginRes = http.post('https://api.example.com/auth/login', JSON.stringify({
    email: user.email,
    password: user.password
  }), {
    headers: { 'Content-Type': 'application/json' },
  });

  check(loginRes, {
    'login successful': (r) => r.status === 200,
    'has token': (r) => r.json('token') !== undefined,
  }) || errorRate.add(1);

  const authToken = loginRes.json('token');

  sleep(1);

  // Scenario 2: 瀏覽商品
  let productsRes = http.get('https://api.example.com/products', {
    headers: { 'Authorization': `Bearer ${authToken}` },
  });

  check(productsRes, {
    'products loaded': (r) => r.status === 200,
  }) || errorRate.add(1);

  sleep(2);

  // Scenario 3: 添加到購物車
  const productId = productsRes.json('data.0.id');

  let cartRes = http.post('https://api.example.com/cart/items', JSON.stringify({
    productId: productId,
    quantity: 1
  }), {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authToken}`
    },
  });

  check(cartRes, {
    'item added to cart': (r) => r.status === 201,
  }) || errorRate.add(1);

  sleep(1);

  // Scenario 4: 結帳
  const checkoutStart = Date.now();

  let checkoutRes = http.post('https://api.example.com/orders', JSON.stringify({
    paymentMethod: 'credit_card',
    shippingAddress: user.address
  }), {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authToken}`
    },
  });

  const checkoutTime = Date.now() - checkoutStart;
  checkoutDuration.add(checkoutTime);

  check(checkoutRes, {
    'checkout successful': (r) => r.status === 201,
    'has order id': (r) => r.json('orderId') !== undefined,
  }) || errorRate.add(1);

  sleep(5);
}

// 執行
// k6 run --vus 100 --duration 30s load-test.js
```

### 5.2 壓力測試策略

```yaml
壓力測試類型:

1. Smoke Test (冒煙測試)
   目的: 驗證系統基本功能
   配置: 最小負載 (1-10 用戶)
   時間: 1-2 分鐘

2. Load Test (負載測試)
   目的: 測試預期負載下的表現
   配置: 正常負載 (100-500 用戶)
   時間: 10-30 分鐘

3. Stress Test (壓力測試)
   目的: 找出系統極限
   配置: 逐步增加到崩潰點
   時間: 30-60 分鐘

4. Spike Test (峰值測試)
   目的: 測試突然流量增加
   配置: 瞬間增加到峰值,然後降下
   時間: 5-15 分鐘

5. Soak Test (浸泡測試)
   目的: 檢測記憶體洩漏等長時間問題
   配置: 中等負載
   時間: 數小時到數天
```

---

## Part 6: 安全性測試

### 6.1 SAST (靜態應用安全測試)

**SonarQube 整合與 Semgrep 規則實作**

```yaml
# .github/workflows/sast.yml
name: SAST Security Scan

on:
  push:
    branches: [main, develop]

jobs:
  sonarqube:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0

      - name: Run tests with coverage
        run: npm test -- --coverage

      - name: SonarQube Scan
        uses: sonarsource/sonarqube-scan-action@master
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
          SONAR_HOST_URL: ${{ secrets.SONAR_HOST_URL }}

      - name: Quality Gate Check
        uses: sonarsource/sonarqube-quality-gate-action@master
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

### 6.2 DAST 與依賴漏洞掃描

**OWASP ZAP 與 npm audit 自動化整合**

```javascript
// security-tests/dast-zap.test.js
const ZapClient = require('zaproxy');

describe('DAST Security Tests', () => {
  let zap;
  const targetUrl = process.env.TARGET_URL || 'http://localhost:3000';

  beforeAll(async () => {
    zap = new ZapClient({
      apiKey: process.env.ZAP_API_KEY,
      proxy: { host: 'localhost', port: 8080 }
    });
    await zap.spider.scan(targetUrl);
  });

  test('should not have high risk vulnerabilities', async () => {
    const alerts = await zap.core.alerts(targetUrl);
    const highRisk = alerts.filter(a => a.risk === 'High');

    expect(highRisk).toHaveLength(0);
  }, 300000); // 5 minute timeout

  test('should scan for SQL injection', async () => {
    await zap.ascan.scan(targetUrl, {
      scanPolicyName: 'SQL-Injection'
    });

    const sqlAlerts = await zap.core.alerts(targetUrl);
    const sqlInjection = sqlAlerts.filter(a =>
      a.alert.includes('SQL Injection')
    );

    expect(sqlInjection).toHaveLength(0);
  });

  test('should check for XSS vulnerabilities', async () => {
    const xssAlerts = await zap.core.alerts(targetUrl);
    const xss = xssAlerts.filter(a =>
      a.alert.includes('Cross Site Scripting')
    );

    expect(xss).toHaveLength(0);
  });
});
```

```yaml
# .github/workflows/dependency-scan.yml
name: Dependency Vulnerability Scan

on: [push, pull_request]

jobs:
  npm-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run npm audit
        run: npm audit --audit-level=moderate

      - name: Snyk Security Scan
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high
```

---

## Part 7: 測試資料管理

### 7.1 Test Data Builder Pattern

使用 Faker.js 和 Builder Pattern 建立可重複使用的測試資料

```javascript
// test-utils/builders/UserBuilder.js
const { faker } = require('@faker-js/faker');

class UserBuilder {
  constructor() {
    this.user = {
      email: faker.internet.email(),
      password: 'Test1234!',
      firstName: faker.person.firstName(),
      lastName: faker.person.lastName(),
      role: 'user',
      isActive: true
    };
  }

  withEmail(email) {
    this.user.email = email;
    return this;
  }

  withRole(role) {
    this.user.role = role;
    return this;
  }

  asAdmin() {
    this.user.role = 'admin';
    return this;
  }

  inactive() {
    this.user.isActive = false;
    return this;
  }

  build() {
    return { ...this.user };
  }

  async create(db) {
    const user = this.build();
    const created = await db.users.create(user);
    return created;
  }
}

// 使用範例
describe('User Management', () => {
  test('should create admin user', async () => {
    const adminUser = new UserBuilder()
      .withEmail('admin@example.com')
      .asAdmin()
      .build();

    const response = await request(app)
      .post('/api/users')
      .send(adminUser);

    expect(response.status).toBe(201);
    expect(response.body.role).toBe('admin');
  });

  test('should handle inactive user login', async () => {
    const inactiveUser = await new UserBuilder()
      .inactive()
      .create(db);

    const response = await request(app)
      .post('/api/auth/login')
      .send({
        email: inactiveUser.email,
        password: 'Test1234!'
      });

    expect(response.status).toBe(403);
    expect(response.body.error).toContain('Account is inactive');
  });
});
```

### 7.2 資料庫 Seeding 與資料隔離

測試前自動 seed 資料,測試後自動清理,確保測試獨立性

```javascript
// test-utils/db-helpers.js
const { PrismaClient } = require('@prisma/client');

class TestDatabase {
  constructor() {
    this.prisma = new PrismaClient();
  }

  async seed() {
    // 清空現有資料
    await this.clean();

    // 創建測試資料
    const users = await Promise.all([
      this.prisma.user.create({
        data: {
          email: 'user1@test.com',
          password: 'hashed_password',
          role: 'user'
        }
      }),
      this.prisma.user.create({
        data: {
          email: 'admin@test.com',
          password: 'hashed_password',
          role: 'admin'
        }
      })
    ]);

    // 創建關聯資料
    await this.prisma.post.createMany({
      data: [
        { title: 'Post 1', authorId: users[0].id },
        { title: 'Post 2', authorId: users[0].id }
      ]
    });

    return { users };
  }

  async clean() {
    // 依照 foreign key 順序刪除
    await this.prisma.comment.deleteMany();
    await this.prisma.post.deleteMany();
    await this.prisma.user.deleteMany();
  }

  async disconnect() {
    await this.prisma.$disconnect();
  }
}

// 測試中使用
describe('Blog API', () => {
  let testDb;

  beforeAll(async () => {
    testDb = new TestDatabase();
    await testDb.seed();
  });

  afterAll(async () => {
    await testDb.clean();
    await testDb.disconnect();
  });

  // 每個測試後恢復到初始狀態
  afterEach(async () => {
    await testDb.seed();
  });

  test('should list all posts', async () => {
    const response = await request(app).get('/api/posts');
    expect(response.body).toHaveLength(2);
  });
});
```

---

## Part 8: CI/CD 整合測試

### 8.1 GitHub Actions 測試工作流

多階段測試 pipeline: 單元測試 → 整合測試 → E2E測試 → 效能測試 → 安全測試

```yaml
# .github/workflows/test.yml
name: Comprehensive Test Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

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

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage/lcov.info
          flags: unit

  integration-tests:
    needs: unit-tests
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"

    steps:
      - uses: actions/checkout@v3
      - name: Run integration tests
        run: npm run test:integration

  e2e-tests:
    needs: integration-tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install Playwright
        run: npx playwright install --with-deps

      - name: Run E2E tests
        run: npm run test:e2e

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: playwright-report/

  performance-tests:
    needs: e2e-tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run K6 load tests
        uses: grafana/k6-action@v0.3.0
        with:
          filename: tests/load-test.js
          cloud: false

  security-tests:
    needs: unit-tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run SAST
        uses: github/super-linter@v4

      - name: Run dependency audit
        run: npm audit --audit-level=moderate
```

### 8.2 測試報告生成

自動生成 HTML 和 JUnit XML 格式報告,整合到 CI/CD

```javascript
// jest.config.js
module.exports = {
  reporters: [
    'default',
    [
      'jest-junit',
      {
        outputDirectory: './test-results',
        outputName: 'junit.xml',
        classNameTemplate: '{classname}',
        titleTemplate: '{title}',
        ancestorSeparator: ' › ',
        usePathForSuiteName: true
      }
    ],
    [
      'jest-html-reporters',
      {
        publicPath: './test-results/html',
        filename: 'report.html',
        expand: true,
        pageTitle: 'Test Report'
      }
    ]
  ],
  collectCoverage: true,
  coverageDirectory: 'coverage',
  coverageReporters: ['html', 'lcov', 'text-summary']
};
```

---

## Part 9: Troubleshooting 測試問題

### 9.1 Flaky Tests 檢測

自動檢測不穩定測試,分析失敗原因和執行時間變異

### 9.2 測試覆蓋率分析

驗證覆蓋率門檻,確保程式碼品質

---

## Part 10: 真實案例研究

### 案例 1: Spotify - 微服務測試策略

**契約測試 (Pact)** - 1000+ 微服務,測試時間從2小時縮短到20分鐘

### 案例 2: Netflix - Chaos Testing

**Chaos Monkey** - 在混沌條件下測試,2015 AWS故障零影響

### 案例 3: Google - 測試金字塔實踐

**70/20/10 比例** - 70%單元測試, 20%整合測試, 10% E2E測試

---

## 總結

本深度技術指南涵蓋了測試的進階主題:

✅ **測試策略** - 測試金字塔、優先級矩陣
✅ **單元測試** - TDD、測試替身、Mock策略
✅ **整合測試** - API測試、資料庫測試、Contract Testing
✅ **E2E測試** - Playwright自動化、Page Object Model
✅ **效能測試** - K6負載測試、壓力測試策略
✅ **安全測試** - SAST/DAST、依賴漏洞掃描、OWASP ZAP
✅ **測試資料管理** - Test Data Builder、資料庫Seeding、資料隔離
✅ **CI/CD整合** - GitHub Actions工作流、測試報告生成
✅ **Troubleshooting** - Flaky tests檢測、覆蓋率分析
✅ **真實案例** - Spotify契約測試、Netflix Chaos Testing、Google測試金字塔

### 關鍵要點

1. **測試金字塔**: 大量快速單元測試,少量慢速E2E測試
2. **測試隔離**: 每個測試獨立,可並行執行
3. **持續測試**: 整合到CI/CD,快速反饋
4. **測試資料**: 使用Builder Pattern,避免測試間干擾
5. **品質優先**: 寧可少而精,不要多而不穩定

---

## 📚 延伸閱讀

- [Testing SOP 完整版](./SOP.md)
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

### 相關 Skills
- `/testing-strategy` - 測試策略設計、測試金字塔建立
- `/qa-testing` - 測試計畫、驗收測試、測試案例撰寫
- `/security-audit` - 安全測試（OWASP Top 10、SAST/DAST）
- `/performance-optimization` - 效能基準測試、負載測試
- `/devops-github-actions` - GitHub Actions CI 測試整合
- `/devops-docker` - Docker 測試環境建置
- `/devops-monitoring` - 測試指標監控與儀表板
- `/code-review` - 程式碼審查與測試品質
- `/integration-database` - 資料庫測試（PostgreSQL）
- `/mobile-development` - 行動端測試（涉及 Android/iOS/macOS 時）

---

**文檔版本: v0.01
**最後更新**: 2025-10-29
**維護者**: AISDLC Framework Team
