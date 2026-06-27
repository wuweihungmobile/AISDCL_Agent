# Refactoring 程式碼重構 - 深度技術指南
# Deep Dive Technical Guide

**版本**: v0.01
**最後更新**: 2025-10-29
**適用對象**: 經驗豐富的開發者、技術架構師、代碼審查專家
**建議閱讀**: 先閱讀 SOP_QuickRef.md 和 SOP.md
**文檔類型**: 技術參考、最佳實踐、深度分析

---

## 📚 文檔說明

### 何時閱讀此文檔

✅ **適合閱讀的情況**:
- 面對高複雜度代碼需要系統性重構
- 需要制定大規模重構計劃
- 處理複雜的設計模式應用
- 進行架構層級的重構
- 需要重構遺留代碼但缺乏測試覆蓋
- 學習進階重構技巧和模式

❌ **不建議閱讀的情況**:
- 初次進行程式碼重構(請閱讀 SOP.md)
- 快速參考重構步驟(請閱讀 SOP_QuickRef.md)
- 簡單的變數重命名或格式調整

### 文檔結構

```
Part 1: 代碼異味識別大全
Part 2: 重構模式深度解析
Part 3: 大規模重構策略
Part 4: 測試驅動重構 (TDR)
Part 5: 設計模式重構
Part 6: 效能導向重構
Part 7: 架構層級重構
Part 8: 自動化重構工具
Part 9: 重構風險管理
Part 10: 真實案例研究
Part 11: 技術棧遷移深度指南
```

### SOP 階段與 Part 對應表

| SOP 階段 | 對應 Part | 說明 |
|---------|----------|------|
| 階段 1 啟動 | - | AISDLC_INIT.md 載入（見 SOP.md） |
| 階段 2 品質分析 | Part 1 | 代碼異味識別大全 |
| 階段 3 目標設定 | Part 9 | 重構風險管理 |
| 階段 4 策略制定 | Part 2, 3 | 重構模式深度解析、大規模重構策略 |
| 階段 5 實作 | Part 4, 5, 8 | TDR、設計模式重構、自動化工具 |
| 階段 6 驗證 | Part 6 | 效能導向重構 |
| 階段 7 對比展示 | Part 10 | 真實案例研究 |
| 階段 8 知識沉澱 | Part 7 | 架構層級重構（回顧與歸納） |
| 技術棧遷移專項 | Part 11 | 技術棧遷移深度指南（搭配 Migration SOP 或 Refactoring SOP 2.5/4.2.1） |

### 相關場景參考

本文檔專注於程式碼重構，以下相關場景可提供補充視角：

- **[Testing 測試策略](../testing/SOP_DeepDive.md)** - Part 4 測試驅動重構時，參考完整的測試策略和工具
- **[Performance 效能優化](../performance/SOP_DeepDive.md)** - Part 6 效能導向重構的詳細分析和最佳化技術
- **[Brownfield 舊專案維護](../brownfield/SOP_DeepDive.md)** - 在缺乏測試的遺留系統中進行重構的策略
- **[DevOps 持續交付](../devops/SOP_DeepDive.md)** - 如何在 CI/CD pipeline 中整合自動化重構檢查
- **[Migration 技術棧遷移](../migration/SOP.md)** - 全技術棧遷移的完整 SOP（本文 Part 11 提供深度技術指南）

---

## Part 1: 代碼異味識別大全

### 1.1 代碼異味分類體系

#### Level 1: 基礎代碼異味

**Long Method (過長方法)**:

```javascript
// ❌ 代碼異味: Long Method (100+ 行)
function processOrder(order) {
  // 驗證 (20 行)
  if (!order.items || order.items.length === 0) {
    throw new Error('Order must have items');
  }
  for (let item of order.items) {
    if (!item.productId || !item.quantity) {
      throw new Error('Invalid item');
    }
  }

  // 計算價格 (30 行)
  let total = 0;
  for (let item of order.items) {
    let price = getProductPrice(item.productId);
    let discount = 0;
    if (order.customer.vip) {
      discount = price * 0.1;
    }
    if (item.quantity > 10) {
      discount += price * 0.05;
    }
    total += (price - discount) * item.quantity;
  }

  // 處理付款 (30 行)
  let paymentResult;
  if (order.paymentMethod === 'credit_card') {
    // ...信用卡處理邏輯
  } else if (order.paymentMethod === 'paypal') {
    // ...PayPal 處理邏輯
  }

  // 更新庫存 (20 行)
  for (let item of order.items) {
    let product = getProduct(item.productId);
    product.stock -= item.quantity;
    updateProduct(product);
  }

  return { orderId: generateId(), total, paymentResult };
}

// ✅ 重構後: Extract Method
function processOrder(order) {
  validateOrder(order);
  const total = calculateTotal(order);
  const paymentResult = processPayment(order, total);
  updateInventory(order.items);

  return createOrderResult(total, paymentResult);
}

function validateOrder(order) {
  if (!order.items || order.items.length === 0) {
    throw new Error('Order must have items');
  }
  order.items.forEach(validateItem);
}

function validateItem(item) {
  if (!item.productId || !item.quantity) {
    throw new Error('Invalid item');
  }
}

function calculateTotal(order) {
  return order.items.reduce((total, item) => {
    return total + calculateItemPrice(item, order.customer);
  }, 0);
}

function calculateItemPrice(item, customer) {
  const basePrice = getProductPrice(item.productId);
  const discount = calculateDiscount(basePrice, item.quantity, customer);
  return (basePrice - discount) * item.quantity;
}

function calculateDiscount(price, quantity, customer) {
  let discount = 0;
  if (customer.vip) {
    discount += price * 0.1;
  }
  if (quantity > 10) {
    discount += price * 0.05;
  }
  return discount;
}

function processPayment(order, total) {
  const paymentStrategies = {
    'credit_card': processCreditCardPayment,
    'paypal': processPayPalPayment
  };

  const processor = paymentStrategies[order.paymentMethod];
  if (!processor) {
    throw new Error(`Unsupported payment method: ${order.paymentMethod}`);
  }

  return processor(order, total);
}

function updateInventory(items) {
  items.forEach(item => {
    decreaseStock(item.productId, item.quantity);
  });
}

function createOrderResult(total, paymentResult) {
  return {
    orderId: generateId(),
    total,
    paymentResult
  };
}
```

**Large Class (過大類)**:

```typescript
// ❌ 代碼異味: Large Class (God Object)
class UserManager {
  // 用戶CRUD
  createUser(data) { /* ... */ }
  updateUser(id, data) { /* ... */ }
  deleteUser(id) { /* ... */ }
  getUser(id) { /* ... */ }

  // 認證
  login(email, password) { /* ... */ }
  logout(userId) { /* ... */ }
  resetPassword(email) { /* ... */ }

  // 權限
  hasPermission(userId, resource) { /* ... */ }
  grantPermission(userId, permission) { /* ... */ }

  // 通知
  sendWelcomeEmail(userId) { /* ... */ }
  sendPasswordResetEmail(email) { /* ... */ }

  // 統計
  getUserCount() { /* ... */ }
  getActiveUsers() { /* ... */ }
  getUsersByRole(role) { /* ... */ }
}

// ✅ 重構後: Extract Class
// 拆分為多個單一職責類

class UserRepository {
  async create(data: UserData): Promise<User> { /* ... */ }
  async update(id: string, data: Partial<UserData>): Promise<User> { /* ... */ }
  async delete(id: string): Promise<void> { /* ... */ }
  async findById(id: string): Promise<User | null> { /* ... */ }
  async findByEmail(email: string): Promise<User | null> { /* ... */ }
}

class AuthenticationService {
  constructor(
    private userRepo: UserRepository,
    private tokenService: TokenService
  ) {}

  async login(email: string, password: string): Promise<AuthToken> {
    const user = await this.userRepo.findByEmail(email);
    if (!user || !await this.verifyPassword(user, password)) {
      throw new AuthenticationError('Invalid credentials');
    }
    return this.tokenService.generate(user);
  }

  async logout(userId: string): Promise<void> {
    await this.tokenService.revoke(userId);
  }

  async resetPassword(email: string): Promise<void> {
    const user = await this.userRepo.findByEmail(email);
    if (user) {
      const resetToken = await this.tokenService.generateResetToken(user);
      await this.notificationService.sendPasswordReset(email, resetToken);
    }
  }

  private async verifyPassword(user: User, password: string): Promise<boolean> {
    return bcrypt.compare(password, user.passwordHash);
  }
}

class AuthorizationService {
  constructor(private userRepo: UserRepository) {}

  async hasPermission(userId: string, resource: string, action: string): Promise<boolean> {
    const user = await this.userRepo.findById(userId);
    if (!user) return false;

    return user.permissions.some(p =>
      p.resource === resource && p.actions.includes(action)
    );
  }

  async grantPermission(userId: string, permission: Permission): Promise<void> {
    const user = await this.userRepo.findById(userId);
    if (!user) throw new NotFoundError('User not found');

    user.permissions.push(permission);
    await this.userRepo.update(userId, { permissions: user.permissions });
  }
}

class UserNotificationService {
  constructor(private emailService: EmailService) {}

  async sendWelcomeEmail(user: User): Promise<void> {
    await this.emailService.send({
      to: user.email,
      subject: 'Welcome!',
      template: 'welcome',
      data: { name: user.name }
    });
  }

  async sendPasswordReset(email: string, resetToken: string): Promise<void> {
    await this.emailService.send({
      to: email,
      subject: 'Password Reset',
      template: 'password-reset',
      data: { resetToken }
    });
  }
}

class UserStatisticsService {
  constructor(private userRepo: UserRepository) {}

  async getTotalUserCount(): Promise<number> {
    return this.userRepo.count();
  }

  async getActiveUserCount(since: Date): Promise<number> {
    return this.userRepo.count({ lastActive: { $gte: since } });
  }

  async getUsersByRole(role: string): Promise<User[]> {
    return this.userRepo.find({ role });
  }
}
```

**Duplicated Code (重複代碼)**:

```python
# ❌ 代碼異味: Duplicated Code
class ReportGenerator:
    def generate_user_report(self):
        # 連接資料庫
        conn = psycopg2.connect(
            host="localhost",
            database="mydb",
            user="user",
            password="password"
        )
        cursor = conn.cursor()

        # 查詢資料
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()

        # 生成報表
        report = []
        for user in users:
            report.append({
                'id': user[0],
                'name': user[1],
                'email': user[2]
            })

        # 關閉連接
        cursor.close()
        conn.close()

        return report

    def generate_order_report(self):
        # 連接資料庫 (重複!)
        conn = psycopg2.connect(
            host="localhost",
            database="mydb",
            user="user",
            password="password"
        )
        cursor = conn.cursor()

        # 查詢資料
        cursor.execute("SELECT * FROM orders")
        orders = cursor.fetchall()

        # 生成報表
        report = []
        for order in orders:
            report.append({
                'id': order[0],
                'user_id': order[1],
                'total': order[2]
            })

        # 關閉連接 (重複!)
        cursor.close()
        conn.close()

        return report

# ✅ 重構後: Extract Method + Template Method
class ReportGenerator:
    def __init__(self, db_config):
        self.db_config = db_config

    def generate_user_report(self):
        return self._generate_report(
            "SELECT * FROM users",
            self._format_user_row
        )

    def generate_order_report(self):
        return self._generate_report(
            "SELECT * FROM orders",
            self._format_order_row
        )

    # Template Method
    def _generate_report(self, query, formatter):
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()

            return [formatter(row) for row in rows]

    # 提取通用方法
    def _get_db_connection(self):
        return psycopg2.connect(**self.db_config)

    # 格式化方法
    def _format_user_row(self, row):
        return {
            'id': row[0],
            'name': row[1],
            'email': row[2]
        }

    def _format_order_row(self, row):
        return {
            'id': row[0],
            'user_id': row[1],
            'total': row[2]
        }
```

#### Level 2: 進階代碼異味

**Feature Envy (依戀情結)**:

```java
// ❌ 代碼異味: Feature Envy
public class OrderProcessor {
    public double calculateTotal(Order order) {
        double total = 0;

        // 過度使用 Order 的內部資料
        for (OrderItem item : order.getItems()) {
            double price = item.getProduct().getPrice();
            int quantity = item.getQuantity();
            double discount = item.getDiscount();

            total += (price * quantity) - discount;
        }

        // 還使用 Customer 的資料
        if (order.getCustomer().isVIP()) {
            total *= 0.9; // 10% VIP 折扣
        }

        return total;
    }
}

// ✅ 重構後: Move Method
public class Order {
    private List<OrderItem> items;
    private Customer customer;

    public double calculateTotal() {
        double subtotal = items.stream()
            .mapToDouble(OrderItem::calculatePrice)
            .sum();

        return customer.applyDiscount(subtotal);
    }
}

public class OrderItem {
    private Product product;
    private int quantity;
    private double discount;

    public double calculatePrice() {
        return (product.getPrice() * quantity) - discount;
    }
}

public class Customer {
    private boolean vip;

    public double applyDiscount(double amount) {
        return vip ? amount * 0.9 : amount;
    }
}

public class OrderProcessor {
    // 現在只需調用
    public double calculateTotal(Order order) {
        return order.calculateTotal();
    }
}
```

**Primitive Obsession (基本型別偏執)**:

```typescript
// ❌ 代碼異味: Primitive Obsession
class UserService {
  createUser(
    email: string,
    password: string,
    phone: string,
    zipCode: string
  ) {
    // 驗證邏輯散落各處
    if (!/^\S+@\S+\.\S+$/.test(email)) {
      throw new Error('Invalid email');
    }

    if (password.length < 8) {
      throw new Error('Password too short');
    }

    if (!/^\d{10}$/.test(phone)) {
      throw new Error('Invalid phone');
    }

    if (!/^\d{5}$/.test(zipCode)) {
      throw new Error('Invalid zip code');
    }

    // ...
  }

  updateUserEmail(userId: string, newEmail: string) {
    // 又要重複驗證邏輯
    if (!/^\S+@\S+\.\S+$/.test(newEmail)) {
      throw new Error('Invalid email');
    }
    // ...
  }
}

// ✅ 重構後: Replace Primitive with Object (Value Object)
class Email {
  private readonly value: string;

  constructor(value: string) {
    if (!Email.isValid(value)) {
      throw new Error('Invalid email format');
    }
    this.value = value;
  }

  static isValid(email: string): boolean {
    return /^\S+@\S+\.\S+$/.test(email);
  }

  toString(): string {
    return this.value;
  }

  getDomain(): string {
    return this.value.split('@')[1];
  }
}

class Password {
  private readonly hash: string;

  constructor(plaintext: string) {
    if (!Password.isStrong(plaintext)) {
      throw new Error('Password must be at least 8 characters');
    }
    this.hash = this.hashPassword(plaintext);
  }

  static isStrong(password: string): boolean {
    return password.length >= 8 &&
           /[A-Z]/.test(password) &&
           /[a-z]/.test(password) &&
           /[0-9]/.test(password);
  }

  private hashPassword(plaintext: string): string {
    return bcrypt.hashSync(plaintext, 10);
  }

  verify(plaintext: string): boolean {
    return bcrypt.compareSync(plaintext, this.hash);
  }
}

class PhoneNumber {
  private readonly value: string;

  constructor(value: string) {
    const normalized = value.replace(/\D/g, '');
    if (normalized.length !== 10) {
      throw new Error('Phone number must be 10 digits');
    }
    this.value = normalized;
  }

  toString(): string {
    return this.value;
  }

  format(): string {
    return `(${this.value.slice(0, 3)}) ${this.value.slice(3, 6)}-${this.value.slice(6)}`;
  }
}

class ZipCode {
  private readonly value: string;

  constructor(value: string) {
    if (!/^\d{5}$/.test(value)) {
      throw new Error('Zip code must be 5 digits');
    }
    this.value = value;
  }

  toString(): string {
    return this.value;
  }
}

class UserService {
  createUser(
    email: Email,
    password: Password,
    phone: PhoneNumber,
    zipCode: ZipCode
  ) {
    // 不需要驗證 - Value Objects 已確保有效性
    // ...
  }

  updateUserEmail(userId: string, newEmail: Email) {
    // 不需要驗證
    // ...
  }
}

// 使用
const user = userService.createUser(
  new Email('user@example.com'),
  new Password('SecurePass123'),
  new PhoneNumber('1234567890'),
  new ZipCode('12345')
);
```

---

## Part 2: 重構模式深度解析

### 2.1 組織函數 (Composing Methods)

**Extract Function 進階應用**:

```javascript
// 複雜的業務邏輯重構
// Before
function calculatePrice(order) {
  let price = order.quantity * order.itemPrice;

  if (order.quantity > 100) {
    price = price * 0.95;
  } else if (order.quantity > 50) {
    price = price * 0.97;
  }

  if (order.shippingMethod === 'express') {
    price += order.quantity * 0.5;
  } else {
    price += order.quantity * 0.2;
  }

  if (order.customer.loyaltyPoints > 1000) {
    price = price * 0.9;
  }

  return price;
}

// After: 提取多個意圖明確的函數
function calculatePrice(order) {
  const basePrice = calculateBasePrice(order);
  const quantityDiscount = calculateQuantityDiscount(basePrice, order.quantity);
  const shippingCost = calculateShippingCost(order);
  const loyaltyDiscount = calculateLoyaltyDiscount(basePrice, order.customer);

  return basePrice - quantityDiscount + shippingCost - loyaltyDiscount;
}

function calculateBasePrice(order) {
  return order.quantity * order.itemPrice;
}

function calculateQuantityDiscount(basePrice, quantity) {
  if (quantity > 100) {
    return basePrice * 0.05; // 5% 折扣
  } else if (quantity > 50) {
    return basePrice * 0.03; // 3% 折扣
  }
  return 0;
}

function calculateShippingCost(order) {
  const rates = {
    'express': 0.5,
    'standard': 0.2
  };
  return order.quantity * (rates[order.shippingMethod] || rates['standard']);
}

function calculateLoyaltyDiscount(basePrice, customer) {
  return customer.loyaltyPoints > 1000 ? basePrice * 0.1 : 0;
}
```

### 2.2 在對象之間移動特性 (Moving Features Between Objects)

**Move Method + Move Field**:

```typescript
// Before: Account 類做太多事
class Account {
  private _type: string;
  private _daysOverdrawn: number;
  private _interestRate: number;

  overdraftCharge(): number {
    if (this._type === 'premium') {
      return this._daysOverdrawn > 7 ? (this._daysOverdrawn - 7) * 2.5 : 0;
    } else {
      return this._daysOverdrawn * 1.75;
    }
  }

  bankCharge(): number {
    let result = 4.5;
    if (this._daysOverdrawn > 0) {
      result += this.overdraftCharge();
    }
    return result;
  }
}

// After: 引入 AccountType 類
class AccountType {
  constructor(private _name: string) {}

  isPremium(): boolean {
    return this._name === 'premium';
  }

  overdraftCharge(daysOverdrawn: number): number {
    if (this.isPremium()) {
      return daysOverdrawn > 7 ? (daysOverdrawn - 7) * 2.5 : 0;
    } else {
      return daysOverdrawn * 1.75;
    }
  }
}

class Account {
  private _type: AccountType;
  private _daysOverdrawn: number;

  constructor(type: string) {
    this._type = new AccountType(type);
  }

  overdraftCharge(): number {
    return this._type.overdraftCharge(this._daysOverdrawn);
  }

  bankCharge(): number {
    let result = 4.5;
    if (this._daysOverdrawn > 0) {
      result += this.overdraftCharge();
    }
    return result;
  }
}
```

---

## Part 3: 大規模重構策略

### 3.1 Mikado Method (米卡多方法)

**適用場景**: 複雜依賴關係的大型重構

```yaml
Mikado Method 步驟:

1. 設定目標
   - 明確定義重構目標
   - 例如: "將支付邏輯從 OrderService 提取到獨立的 PaymentService"

2. 嘗試直接實現
   - 進行變更
   - 運行測試
   - 記錄失敗

3. 回退變更
   - 恢復到穩定狀態
   - 保持代碼可工作

4. 識別前置條件
   - 分析失敗原因
   - 列出必須先完成的子任務

5. 繪製 Mikado 圖
   ```
   [目標: 提取 PaymentService]
          ↑
          ├── [先決條件 1: 解耦 Order 和 Payment 資料模型]
          │   ↑
          │   ├── [1.1: 建立 Payment 資料表]
          │   └── [1.2: 遷移現有資料]
          │
          ├── [先決條件 2: 提取支付介面]
          │   ↑
          │   ├── [2.1: 定義 IPaymentProcessor]
          │   └── [2.2: 實作適配器]
          │
          └── [先決條件 3: 更新測試]
              ↑
              ├── [3.1: 建立 PaymentService 單元測試]
              └── [3.2: 更新整合測試]
   ```

6. 從葉子節點開始實施
   - 先完成最底層的前置條件
   - 逐步向上完成
   - 每步都確保測試通過

7. 重複直到達成目標
```

### 3.2 Parallel Change (並行變更) 進階應用

```javascript
// 大規模 API 變更: 從回調改為 Promise

// Phase 1: Expand - 支援兩種模式
class UserService {
  // 舊 API (保留)
  getUser(id, callback) {
    console.warn('getUser with callback is deprecated. Use getUserAsync instead.');

    this.getUserAsync(id)
      .then(user => callback(null, user))
      .catch(err => callback(err));
  }

  // 新 API
  async getUserAsync(id) {
    const user = await this.userRepository.findById(id);
    if (!user) {
      throw new Error('User not found');
    }
    return user;
  }
}

// Phase 2: Migrate - 逐步遷移調用方
// 舊代碼
userService.getUser('123', (err, user) => {
  if (err) {
    console.error(err);
  } else {
    console.log(user);
  }
});

// 遷移後
try {
  const user = await userService.getUserAsync('123');
  console.log(user);
} catch (err) {
  console.error(err);
}

// Phase 3: Contract - 移除舊 API
class UserService {
  async getUser(id) { // 重命名為 getUser,移除 Async 後綴
    const user = await this.userRepository.findById(id);
    if (!user) {
      throw new Error('User not found');
    }
    return user;
  }
}
```

---

## Part 4: 測試驅動重構 (TDR)

### 4.1 紅-綠-重構循環進階

```python
# 實例: 重構複雜的報價計算邏輯

# Step 1: 為既有代碼添加特性測試 (紅 - 建立測試)
import unittest

class QuoteCalculatorTest(unittest.TestCase):
    def test_basic_quote_calculation(self):
        calculator = QuoteCalculator()
        quote = calculator.calculate({
            'items': [
                {'name': 'Widget', 'quantity': 10, 'price': 5.0}
            ],
            'customer_type': 'regular',
            'delivery': 'standard'
        })

        self.assertEqual(quote['subtotal'], 50.0)
        self.assertEqual(quote['delivery_fee'], 10.0)
        self.assertEqual(quote['total'], 60.0)

    def test_premium_customer_discount(self):
        calculator = QuoteCalculator()
        quote = calculator.calculate({
            'items': [
                {'name': 'Widget', 'quantity': 10, 'price': 5.0}
            ],
            'customer_type': 'premium',
            'delivery': 'standard'
        })

        # Premium customers get 10% discount
        self.assertEqual(quote['subtotal'], 50.0)
        self.assertEqual(quote['discount'], 5.0)
        self.assertEqual(quote['total'], 55.0)

# Step 2: 運行測試確保通過 (綠)
# $ python -m pytest tests/test_quote_calculator.py

# Step 3: 重構 (保持測試綠燈)
class QuoteCalculator:
    # 重構前: 一個大函數
    def calculate_old(self, request):
        subtotal = sum(item['quantity'] * item['price'] for item in request['items'])

        discount = 0
        if request['customer_type'] == 'premium':
            discount = subtotal * 0.1
        elif request['customer_type'] == 'vip':
            discount = subtotal * 0.15

        delivery_fee = 10.0 if request['delivery'] == 'standard' else 20.0

        total = subtotal - discount + delivery_fee

        return {
            'subtotal': subtotal,
            'discount': discount,
            'delivery_fee': delivery_fee,
            'total': total
        }

    # 重構後: 提取方法
    def calculate(self, request):
        subtotal = self._calculate_subtotal(request['items'])
        discount = self._calculate_discount(subtotal, request['customer_type'])
        delivery_fee = self._calculate_delivery_fee(request['delivery'])
        total = subtotal - discount + delivery_fee

        return self._create_quote(subtotal, discount, delivery_fee, total)

    def _calculate_subtotal(self, items):
        return sum(item['quantity'] * item['price'] for item in items)

    def _calculate_discount(self, subtotal, customer_type):
        discount_rates = {
            'premium': 0.10,
            'vip': 0.15,
            'regular': 0.0
        }
        return subtotal * discount_rates.get(customer_type, 0.0)

    def _calculate_delivery_fee(self, delivery_method):
        fees = {
            'standard': 10.0,
            'express': 20.0,
            'overnight': 30.0
        }
        return fees.get(delivery_method, 10.0)

    def _create_quote(self, subtotal, discount, delivery_fee, total):
        return {
            'subtotal': subtotal,
            'discount': discount,
            'delivery_fee': delivery_fee,
            'total': total
        }

# Step 4: 再次運行測試確保通過
# $ python -m pytest tests/test_quote_calculator.py

# Step 5: 進一步重構 - 引入策略模式
from abc import ABC, abstractmethod

class DiscountStrategy(ABC):
    @abstractmethod
    def calculate(self, subtotal):
        pass

class NoDiscount(DiscountStrategy):
    def calculate(self, subtotal):
        return 0.0

class PercentageDiscount(DiscountStrategy):
    def __init__(self, percentage):
        self.percentage = percentage

    def calculate(self, subtotal):
        return subtotal * self.percentage

class QuoteCalculator:
    def __init__(self):
        self.discount_strategies = {
            'regular': NoDiscount(),
            'premium': PercentageDiscount(0.10),
            'vip': PercentageDiscount(0.15)
        }

    def calculate(self, request):
        subtotal = self._calculate_subtotal(request['items'])

        strategy = self.discount_strategies.get(request['customer_type'], NoDiscount())
        discount = strategy.calculate(subtotal)

        delivery_fee = self._calculate_delivery_fee(request['delivery'])
        total = subtotal - discount + delivery_fee

        return self._create_quote(subtotal, discount, delivery_fee, total)

    # ... 其他方法保持不變

# 測試仍然通過 ✅
```

---

## Part 5: 設計模式重構

### 5.1 從程序式代碼到物件導向

**Replace Conditional with Polymorphism**:

```java
// Before: 使用 switch 處理不同類型
public class EmployeePayroll {
    public double calculatePay(Employee employee) {
        switch (employee.getType()) {
            case FULL_TIME:
                return employee.getMonthlySalary();

            case PART_TIME:
                return employee.getHourlyRate() * employee.getHoursWorked();

            case CONTRACTOR:
                double amount = employee.getHourlyRate() * employee.getHoursWorked();
                return amount * 1.1; // 加 10% 管理費

            default:
                throw new IllegalArgumentException("Unknown employee type");
        }
    }

    public double calculateBonus(Employee employee) {
        switch (employee.getType()) {
            case FULL_TIME:
                return employee.getMonthlySalary() * 0.1; // 10% 年終獎金

            case PART_TIME:
                return 0; // 無獎金

            case CONTRACTOR:
                return 0; // 無獎金

            default:
                throw new IllegalArgumentException("Unknown employee type");
        }
    }
}

// After: 使用多型
public abstract class Employee {
    protected String name;
    protected String id;

    public abstract double calculatePay();
    public abstract double calculateBonus();
}

public class FullTimeEmployee extends Employee {
    private double monthlySalary;

    @Override
    public double calculatePay() {
        return monthlySalary;
    }

    @Override
    public double calculateBonus() {
        return monthlySalary * 0.1;
    }
}

public class PartTimeEmployee extends Employee {
    private double hourlyRate;
    private int hoursWorked;

    @Override
    public double calculatePay() {
        return hourlyRate * hoursWorked;
    }

    @Override
    public double calculateBonus() {
        return 0;
    }
}

public class Contractor extends Employee {
    private double hourlyRate;
    private int hoursWorked;

    @Override
    public double calculatePay() {
        double baseAmount = hourlyRate * hoursWorked;
        return baseAmount * 1.1; // 加管理費
    }

    @Override
    public double calculateBonus() {
        return 0;
    }
}

public class EmployeePayroll {
    public double calculatePay(Employee employee) {
        return employee.calculatePay();
    }

    public double calculateBonus(Employee employee) {
        return employee.calculateBonus();
    }
}
```

---

## Part 6: 效能導向重構

### 6.1 優化演算法複雜度

```javascript
// Before: O(n²) 複雜度
function findDuplicates(array) {
  const duplicates = [];

  for (let i = 0; i < array.length; i++) {
    for (let j = i + 1; j < array.length; j++) {
      if (array[i] === array[j] && !duplicates.includes(array[i])) {
        duplicates.push(array[i]);
      }
    }
  }

  return duplicates;
}

// After: O(n) 複雜度
function findDuplicates(array) {
  const seen = new Set();
  const duplicates = new Set();

  for (const item of array) {
    if (seen.has(item)) {
      duplicates.add(item);
    } else {
      seen.add(item);
    }
  }

  return Array.from(duplicates);
}

// 效能測試
const largeArray = Array.from({ length: 10000 }, () => Math.floor(Math.random() * 1000));

console.time('O(n²)');
findDuplicates_old(largeArray);
console.timeEnd('O(n²)'); // ~500ms

console.time('O(n)');
findDuplicates(largeArray);
console.timeEnd('O(n)'); // ~5ms
```

---

## Part 7: 架構層級重構

### 7.1 Layer by Layer 重構

```yaml
分層架構重構步驟:

Before: 所有代碼混在一起
  ├── routes.js (路由、業務邏輯、資料庫查詢全部混在一起)
  ├── utils.js
  └── config.js

After: 清晰分層
  ├── presentation/       # 表現層
  │   ├── routes/
  │   ├── controllers/
  │   └── middleware/
  ├── application/        # 應用層
  │   ├── services/
  │   └── use-cases/
  ├── domain/            # 領域層
  │   ├── entities/
  │   ├── value-objects/
  │   └── repositories/
  └── infrastructure/    # 基礎設施層
      ├── database/
      ├── external-services/
      └── config/
```

---

## Part 8: 自動化重構工具

### 8.1 IDE 重構功能

```yaml
常用 IDE 重構快捷鍵:

Visual Studio Code:
  - F2: 重命名符號
  - Ctrl+Shift+R: 重構菜單
  - Ctrl+.: 快速修復

JetBrains IDEs:
  - Shift+F6: 重命名
  - Ctrl+Alt+M: 提取方法
  - Ctrl+Alt+V: 提取變數
  - Ctrl+Alt+C: 提取常數
  - Ctrl+Alt+P: 提取參數
```

### 8.2 程式碼自動化重構

```bash
# JSCodeshift - JavaScript 重構工具
npx jscodeshift -t transform.js src/

# Example transform: 將 var 轉換為 const/let
# transform.js
module.exports = function(fileInfo, api) {
  const j = api.jscodeshift;
  const root = j(fileInfo.source);

  root.find(j.VariableDeclaration, { kind: 'var' })
    .forEach(path => {
      const declaration = path.value;
      const hasReassignment = false; // 檢查是否有重新賦值

      declaration.kind = hasReassignment ? 'let' : 'const';
    });

  return root.toSource();
};
```

---

## Part 9: Troubleshooting Guide - 重構問題診斷

### 9.1 重構引入的 Bug

#### 問題 1: 重構後測試失敗

**症狀**:
```
✅ 重構前: 所有測試通過
❌ 重構後: 部分測試失敗
```

**常見原因**:
1. **邏輯改變** - 重構時不小心改變了業務邏輯
2. **邊界條件遺漏** - 新程式碼未處理 edge cases
3. **副作用改變** - 函數的副作用被移除或改變

**診斷步驟**:
```bash
# 1. 確認哪些測試失敗
npm test -- --verbose

# 2. 使用 git bisect 定位問題 commit
git bisect start
git bisect bad HEAD
git bisect good <last-working-commit>

# 3. 對比重構前後的程式碼
git diff <before> <after> path/to/file.js
```

**解決方案**:
```javascript
// ❌ 錯誤: 改變了邏輯
// 重構前
function calculateDiscount(price, isVIP) {
  if (isVIP) {
    return price * 0.8; // 20% off
  }
  return price;
}

// 重構後 (錯誤)
function calculateDiscount(price, isVIP) {
  return isVIP ? price * 0.9 : price; // 誤改為 10% off
}

// ✅ 正確: 保持邏輯不變
function calculateDiscount(price, isVIP) {
  return isVIP ? price * 0.8 : price;
}
```

#### 問題 2: 效能退化

**症狀**: 重構後系統變慢

**診斷工具**:
```javascript
// Node.js 效能分析
const { performance } = require('perf_hooks');

const start = performance.now();
// 執行重構後的程式碼
refactoredFunction();
const end = performance.now();

console.log(`執行時間: ${end - start}ms`);
```

**常見原因**:
1. **過度抽象** - 新增過多間接層
2. **記憶體配置** - 重構中建立過多物件
3. **演算法改變** - 不小心改變了時間複雜度

**解決方案**:
```javascript
// ❌ 過度抽象導致效能問題
function processData(data) {
  return data
    .map(x => validate(x))
    .filter(x => x.isValid)
    .map(x => transform(x))
    .filter(x => x.transformed)
    .map(x => format(x));
}

// ✅ 合併步驟減少迭代
function processData(data) {
  return data.reduce((acc, x) => {
    const validated = validate(x);
    if (!validated.isValid) return acc;

    const transformed = transform(validated);
    if (!transformed.transformed) return acc;

    acc.push(format(transformed));
    return acc;
  }, []);
}
```

### 9.2 依賴破壞修復

#### 問題: Import 路徑破壞

**症狀**:
```
Error: Cannot find module './utils/helper'
```

**原因**: 重構時移動檔案但未更新 import

**自動化修復**:
```bash
# 使用 sed 批量更新 import 路徑
find src -name "*.js" -exec sed -i '' 's/..\/utils\/helper/..\/shared\/helper/g' {} \;

# 或使用 jscodeshift
npx jscodeshift -t fix-imports.js src/
```

#### 問題: 循環依賴

**症狀**:
```
ReferenceError: Cannot access 'User' before initialization
```

**診斷**:
```bash
# 使用 madge 檢查循環依賴
npx madge --circular src/

# 輸出:
# ✗ Found 2 circular dependencies!
# 1) User.js > Order.js > User.js
# 2) Service.js > Repository.js > Service.js
```

**解決方案**:
```javascript
// ❌ 循環依賴
// User.js
import { Order } from './Order.js';
export class User {
  orders: Order[];
}

// Order.js
import { User } from './User.js';
export class Order {
  user: User;
}

// ✅ 使用介面解耦
// types.ts
export interface IUser { id: string; name: string; }
export interface IOrder { id: string; userId: string; }

// User.ts
import type { IOrder } from './types';
export class User {
  orders: IOrder[];
}

// Order.ts
import type { IUser } from './types';
export class Order {
  user: IUser;
}
```

### 9.3 Merge Conflict 處理

#### 大規模重構的 Merge 策略

**策略 1: Mikado Method + Feature Flags**
```javascript
// 使用 Feature Flag 逐步啟用新程式碼
function processOrder(order) {
  if (featureFlags.useRefactoredOrderProcessor) {
    return newProcessOrder(order); // 重構後的程式碼
  }
  return legacyProcessOrder(order); // 舊程式碼
}
```

**策略 2: Parallel Run Pattern**
```javascript
// 同時執行新舊程式碼,比較結果
async function processWithValidation(data) {
  const [oldResult, newResult] = await Promise.all([
    legacyProcess(data),
    refactoredProcess(data)
  ]);

  if (!deepEqual(oldResult, newResult)) {
    logger.error('Refactoring mismatch', { oldResult, newResult });
    return oldResult; // 發現不一致時使用舊結果
  }

  return newResult;
}
```

### 9.4 重構回滾決策

**何時應該回滾**:
1. ✅ 關鍵功能損壞且無法快速修復
2. ✅ 效能退化 > 20% 且影響用戶體驗
3. ✅ 發現重大邏輯錯誤
4. ✅ 部署後錯誤率激增

**回滾步驟**:
```bash
# 1. 立即回滾到上一個穩定版本
git revert <refactoring-commit>
git push origin main

# 2. 或使用 deployment 回滾
kubectl rollout undo deployment/app

# 3. 記錄問題並計劃修復
git commit -m "docs: Record refactoring issues for future fix"
```

**重構後的監控清單**:
```yaml
監控指標:
  - 錯誤率 (Error Rate)
  - 響應時間 (P50, P95, P99)
  - 記憶體使用量
  - CPU 使用率
  - 業務指標 (轉換率、交易量等)

告警閾值:
  - 錯誤率上升 > 2x baseline
  - P95 延遲增加 > 20%
  - 記憶體洩漏偵測
```

---

## Part 10: 真實案例研究

### 案例 1: Uber - 從 Monolith 到 Microservices

#### 背景
- **時間**: 2013-2016
- **問題**: PHP Monolith 無法擴展,開發速度變慢
- **規模**: 單一 Repo 數百萬行程式碼

#### 挑戰
1. **高流量系統** - 無法停機重構
2. **團隊規模** - 數百位工程師同時開發
3. **業務持續成長** - 需要持續交付新功能

#### 解決方案: Strangler Fig Pattern

**階段 1: 建立 API Gateway**
```
[Clients]
    ↓
[API Gateway] ← 路由決策
    ↓      ↘
[Monolith]  [New Service 1]
```

**階段 2: 逐步遷移服務**
```python
# API Gateway 路由邏輯
def route_request(request):
    if request.path.startswith('/trips'):
        if feature_flag('use_trip_service'):
            return trip_service.handle(request)  # 新服務

    return monolith.handle(request)  # 舊 Monolith
```

**階段 3: 資料庫分離**
```
Monolith DB → [Dual Write] → Trip Service DB
                   ↓
            驗證資料一致性
                   ↓
         Trip Service 成為主資料源
```

#### 結果
- ✅ **開發速度提升 3x** - 團隊可獨立開發服務
- ✅ **可擴展性改善** - 可針對瓶頸服務擴展
- ✅ **技術棧多元化** - 從 PHP 遷移到 Go, Java, Node.js
- ✅ **0 停機時間** - 漸進式遷移無需停機

#### 關鍵洞察
1. **漸進式遷移** - 避免大爆炸式重寫
2. **Feature Flags** - 控制流量切換風險
3. **Dual Write** - 資料庫遷移的安全網
4. **監控先行** - 完善的監控系統確保安全

---

### 案例 2: Airbnb - Frontend 重構 (Rails → React)

#### 背景
- **時間**: 2015-2017
- **問題**: Rails + jQuery 前端難以維護,開發體驗差
- **目標**: 遷移到 React 同時保持服務穩定

#### 挑戰
1. **用戶體驗** - 不能影響用戶使用
2. **SEO 要求** - 需要 SSR (Server-Side Rendering)
3. **團隊學習曲線** - 工程師需要學習 React

#### 解決方案: Hybrid Rendering

**架構**:
```
[Rails Server]
    ↓
[Hypernova] ← React SSR 服務
    ↓
[React Components]
    ↓
[Client-side Hydration]
```

**漸進式遷移**:
```ruby
# Rails View 中嵌入 React Component
<%= react_component('SearchBar', {
  location: @location,
  dates: @dates
}) %>

# 舊 jQuery 程式碼依然運作
<script>
  // Legacy jQuery code
  $('#old-widget').doSomething();
</script>
```

**Bridge Pattern**:
```javascript
// 建立 Bridge 讓 React 與 jQuery 共存
class LegacyBridge {
  static mountReact(selector, Component, props) {
    const container = $(selector)[0];
    ReactDOM.render(<Component {...props} />, container);
  }

  static unmountReact(selector) {
    const container = $(selector)[0];
    ReactDOM.unmountComponentAtNode(container);
  }
}

// 使用
LegacyBridge.mountReact('#search-widget', SearchBar, props);
```

#### 結果
- ✅ **開發效率提升 2x** - Component 重用,開發更快
- ✅ **使用者體驗改善** - 更流暢的互動
- ✅ **SEO 維持** - Hypernova 提供 SSR
- ✅ **平滑過渡** - 2 年時間漸進完成,無大問題

#### 關鍵洞察
1. **共存策略** - 新舊技術可以並存
2. **工具支援** - Hypernova 解決 SSR 難題
3. **團隊培訓** - 投資時間培訓工程師
4. **性能監控** - 密切監控 TTI (Time to Interactive)

---

### 案例 3: Shopify - 效能導向重構

#### 背景
- **時間**: 2019-2020
- **問題**: Ruby on Rails 關鍵路徑效能瓶頸
- **影響**: 響應時間 P95 達 150ms,影響用戶體驗

#### 挑戰
1. **識別瓶頸** - 找出真正的效能瓶頸
2. **保持功能** - 重構不能破壞功能
3. **最小化變動** - 只重構關鍵路徑

#### 解決方案: Selective Rewrite with Go

**效能分析**:
```ruby
# 使用 rack-mini-profiler 識別瓶頸
require 'rack-mini-profiler'

Rack::MiniProfiler.config.tap do |c|
  c.enabled = true
end

# 發現: Product listing API 占總時間 60%
```

**關鍵路徑重寫**:
```
[Rails App]
    ↓
[gRPC Call] ← 重寫為 Go 服務
    ↓
[Go Product Service]
    ↓
[Optimized DB Queries]
```

**Go 服務範例**:
```go
// Go 實作的 Product Listing (高效能)
func (s *ProductService) ListProducts(ctx context.Context, req *pb.ListRequest) (*pb.ProductList, error) {
    // 使用連接池和預編譯查詢
    rows, err := s.db.QueryContext(ctx, productListQuery, req.ShopId, req.Limit)
    if err != nil {
        return nil, err
    }
    defer rows.Close()

    products := make([]*pb.Product, 0, req.Limit)
    for rows.Next() {
        var p pb.Product
        if err := rows.Scan(&p.Id, &p.Title, &p.Price); err != nil {
            return nil, err
        }
        products = append(products, &p)
    }

    return &pb.ProductList{Products: products}, nil
}
```

**Rails 整合**:
```ruby
# Rails Controller 呼叫 Go 服務
class ProductsController < ApplicationController
  def index
    # 使用 Go 服務獲取產品列表
    products = GoProductService.list(
      shop_id: current_shop.id,
      limit: params[:limit] || 20
    )

    render json: products
  end
end
```

#### 結果
- ✅ **響應時間改善 70%** - P95 從 150ms → 50ms
- ✅ **吞吐量提升 3x** - 可處理更多請求
- ✅ **成本節省 40%** - 需要更少伺服器
- ✅ **Rails 保留** - 非關鍵路徑仍用 Rails

#### 關鍵洞察
1. **精準重構** - 只重構瓶頸,不做全面重寫
2. **效能優先** - 使用更快的語言處理關鍵路徑
3. **段階式驗證** - A/B Testing 驗證效能改善
4. **保留優勢** - Rails 的開發效率優勢依然保留

---

### 案例對比總結

| 案例 | 重構規模 | 時間 | 策略 | 關鍵成功因素 |
|------|---------|------|------|-------------|
| **Uber** | 完整架構 | 3年 | Strangler Fig | 漸進式,Feature Flags |
| **Airbnb** | Frontend | 2年 | Hybrid Rendering | 共存策略,Bridge Pattern |
| **Shopify** | 關鍵路徑 | 1年 | Selective Rewrite | 精準識別,最小化變動 |

**共同教訓**:
1. ✅ **漸進式優於大爆炸** - 所有案例都採用漸進式重構
2. ✅ **監控至關重要** - 完善的監控確保安全
3. ✅ **保留舊系統** - 新舊並存,逐步切換
4. ✅ **業務持續優先** - 重構不能影響業務

---

## Part 11: 技術棧遷移深度指南

> **適用情境**: 技術棧遷移的深度技術參考指南
> - **全技術棧遷移**（前端+後端+DB+新平台）：搭配 **[Migration SOP](../migration/SOP.md)** 使用
> - **部分技術棧替換**（僅換單層框架）：搭配 **[Refactoring SOP](./SOP.md)** 階段 2.5 / 4.2.1 使用

### 11.1 資料庫遷移技術細節

#### Oracle → PostgreSQL 完整型別映射

```sql
-- 數值型別
NUMBER              → NUMERIC           -- 通用
NUMBER(p)           → NUMERIC(p)        -- 指定精度
NUMBER(p,s)         → NUMERIC(p,s)      -- 指定精度與小數
NUMBER(1)           → BOOLEAN           -- 布林值場景
BINARY_FLOAT        → REAL
BINARY_DOUBLE       → DOUBLE PRECISION
PLS_INTEGER         → INTEGER

-- 字串型別
VARCHAR2(n BYTE)    → VARCHAR(n)
VARCHAR2(n CHAR)    → VARCHAR(n)        -- 注意多位元組差異
NVARCHAR2(n)        → VARCHAR(n)
CHAR(n)             → CHAR(n)
NCHAR(n)            → CHAR(n)
CLOB                → TEXT
NCLOB               → TEXT
LONG                → TEXT

-- 日期時間
DATE                → TIMESTAMP(0)      -- ⚠️ Oracle DATE 含時間
TIMESTAMP           → TIMESTAMP
TIMESTAMP WITH TZ   → TIMESTAMPTZ
INTERVAL YEAR TO MONTH → INTERVAL
INTERVAL DAY TO SECOND → INTERVAL

-- 二進位
BLOB                → BYTEA
RAW(n)              → BYTEA
LONG RAW            → BYTEA
BFILE               → TEXT (存路徑) + 外部檔案

-- 特殊型別
ROWID               → OID / ctid (不建議依賴)
XMLTYPE             → XML
SDO_GEOMETRY        → PostGIS geometry
```

#### SQL 語法轉換進階對照

```sql
-- 1. 分頁查詢
-- Oracle
SELECT * FROM (
  SELECT a.*, ROWNUM rn FROM (
    SELECT * FROM products ORDER BY price DESC
  ) a WHERE ROWNUM <= 20
) WHERE rn > 10;

-- PostgreSQL
SELECT * FROM products ORDER BY price DESC LIMIT 10 OFFSET 10;

-- 2. 遞迴查詢（組織架構樹）
-- Oracle (CONNECT BY)
SELECT emp_id, emp_name, manager_id, LEVEL
FROM employees
START WITH manager_id IS NULL
CONNECT BY PRIOR emp_id = manager_id
ORDER SIBLINGS BY emp_name;

-- PostgreSQL (WITH RECURSIVE)
WITH RECURSIVE emp_tree AS (
  SELECT emp_id, emp_name, manager_id, 1 AS level
  FROM employees WHERE manager_id IS NULL
  UNION ALL
  SELECT e.emp_id, e.emp_name, e.manager_id, t.level + 1
  FROM employees e JOIN emp_tree t ON e.manager_id = t.emp_id
)
SELECT * FROM emp_tree ORDER BY level, emp_name;

-- 3. MERGE 語句 (Upsert)
-- Oracle
MERGE INTO inventory i
USING (SELECT :product_id AS pid, :qty AS qty FROM DUAL) s
ON (i.product_id = s.pid)
WHEN MATCHED THEN UPDATE SET i.quantity = i.quantity + s.qty
WHEN NOT MATCHED THEN INSERT (product_id, quantity) VALUES (s.pid, s.qty);

-- PostgreSQL
INSERT INTO inventory (product_id, quantity) VALUES ($1, $2)
ON CONFLICT (product_id)
DO UPDATE SET quantity = inventory.quantity + EXCLUDED.quantity;

-- 4. Sequence 使用
-- Oracle
INSERT INTO orders (order_id, ...) VALUES (order_seq.NEXTVAL, ...);

-- PostgreSQL (使用 SERIAL 或 IDENTITY)
CREATE TABLE orders (
  order_id BIGINT GENERATED ALWAYS AS IDENTITY,
  ...
);
-- 或使用 Sequence
INSERT INTO orders (order_id, ...) VALUES (nextval('order_seq'), ...);

-- 5. 字串函數
-- Oracle
SELECT SUBSTR(product_name, 1, 10) FROM products;   -- 子字串
SELECT INSTR(product_name, '-') FROM products;       -- 搜尋位置
SELECT LENGTH(product_name) FROM products;            -- 長度
SELECT TRIM(product_name) FROM products;              -- 去空白

-- PostgreSQL
SELECT SUBSTRING(product_name FROM 1 FOR 10) FROM products;
SELECT POSITION('-' IN product_name) FROM products;
SELECT LENGTH(product_name) FROM products;            -- 相同
SELECT TRIM(product_name) FROM products;              -- 相同
```

#### Stored Procedure 遷移決策矩陣

```
SP 分類與遷移策略:

┌─────────────────────┬──────────────────────┬────────────────────┐
│ SP 類型              │ 遷移策略              │ 優先級              │
├─────────────────────┼──────────────────────┼────────────────────┤
│ CRUD 封裝           │ 移至 Spring Data JPA │ 🔴 優先遷移         │
│ 業務計算邏輯         │ 移至 Service Layer   │ 🔴 優先遷移         │
│ 報表彙總查詢         │ 移至 PL/pgSQL        │ 🟡 次要遷移         │
│ ETL 批次處理         │ 移至 Spring Batch    │ 🟡 次要遷移         │
│ 觸發器(審計日誌)     │ 移至 PG Trigger      │ 🟢 直接轉換         │
│ 觸發器(業務邏輯)     │ 移至 Service Layer   │ 🔴 優先遷移         │
│ 暫存/未使用 SP       │ 標記移除              │ ⚪ 清理              │
└─────────────────────┴──────────────────────┴────────────────────┘
```

**經銷存系統 SP 遷移範例**:

```java
// Oracle SP: 庫存異動處理
// CREATE OR REPLACE PROCEDURE sp_inventory_adjust(
//   p_product_id IN NUMBER, p_warehouse_id IN NUMBER,
//   p_qty IN NUMBER, p_type IN VARCHAR2, p_operator IN VARCHAR2
// ) AS ...

// 遷移至 Spring Boot Service
@Service
@Transactional
public class InventoryService {

    private final InventoryRepository inventoryRepo;
    private final InventoryLogRepository logRepo;

    public void adjustInventory(InventoryAdjustRequest request) {
        Inventory inventory = inventoryRepo
            .findByProductIdAndWarehouseId(
                request.getProductId(), request.getWarehouseId())
            .orElseThrow(() -> new NotFoundException("庫存記錄不存在"));

        switch (request.getType()) {
            case IN:
                inventory.increaseQuantity(request.getQuantity());
                break;
            case OUT:
                inventory.decreaseQuantity(request.getQuantity());
                break;
            case ADJUST:
                inventory.setQuantity(request.getQuantity());
                break;
        }

        inventoryRepo.save(inventory);
        logRepo.save(InventoryLog.from(request, inventory));
    }
}
```

---

### 11.2 後端遷移: Python API → Spring Boot

#### API 契約保持策略

```yaml
# 遷移原則: API 路徑和回應格式保持不變
# 舊 Python API
# GET /api/v1/products?category=electronics&page=1&size=20

# 新 Spring Boot API（相同路徑和格式）
# GET /api/v1/products?category=electronics&page=1&size=20
```

```python
# Python (FastAPI) - 舊
@app.get("/api/v1/products")
async def list_products(
    category: str = None,
    page: int = 1,
    size: int = 20
):
    products = await product_service.search(category, page, size)
    return {
        "data": products,
        "pagination": {
            "page": page,
            "size": size,
            "total": total_count
        }
    }
```

```java
// Spring Boot - 新（保持相同 API 契約）
@RestController
@RequestMapping("/api/v1/products")
public class ProductController {

    @GetMapping
    public ResponseEntity<PagedResponse<ProductDTO>> listProducts(
        @RequestParam(required = false) String category,
        @RequestParam(defaultValue = "1") int page,
        @RequestParam(defaultValue = "20") int size
    ) {
        Page<Product> products = productService.search(category, page, size);
        return ResponseEntity.ok(PagedResponse.from(products));
    }
}

// 回應格式保持一致
@Data
public class PagedResponse<T> {
    private List<T> data;
    private PaginationInfo pagination;

    public static <T> PagedResponse<T> from(Page<T> page) {
        PagedResponse<T> response = new PagedResponse<>();
        response.setData(page.getContent());
        response.setPagination(new PaginationInfo(
            page.getNumber() + 1, page.getSize(), page.getTotalElements()
        ));
        return response;
    }
}
```

#### 並行運行架構

```
┌────────────────────────────────────┐
│          Nginx / API Gateway       │
│  ┌──────────────────────────────┐  │
│  │  路由規則 (Feature Flag)     │  │
│  │  /api/v1/products → Spring  │  │
│  │  /api/v1/orders   → Python  │  │ ← 逐模組切換
│  │  /api/v1/reports  → Python  │  │
│  └──────────────────────────────┘  │
├──────────┬─────────────────────────┤
│ Spring   │    Python API           │
│ Boot     │    (舊系統)              │
│ (新系統)  │                         │
├──────────┴─────────────────────────┤
│          PostgreSQL                │
│  (遷移完成後共用同一 DB)            │
└────────────────────────────────────┘
```

---

### 11.3 前端遷移: Vue 3 → React (Next.js)

#### 元件映射對照

| Vue 3 概念 | React/Next.js 對應 | 說明 |
|-----------|-------------------|------|
| `<template>` | JSX return | 模板語法 → JSX |
| `ref()` / `reactive()` | `useState()` | 響應式狀態 |
| `computed()` | `useMemo()` | 計算屬性 |
| `watch()` / `watchEffect()` | `useEffect()` | 副作用/監聽 |
| `onMounted()` | `useEffect(fn, [])` | 生命週期 |
| `provide/inject` | `useContext()` | 依賴注入 |
| `v-model` | `value + onChange` | 雙向綁定 |
| `v-if / v-show` | 條件渲染 `{cond && ...}` | 條件顯示 |
| `v-for` | `array.map()` | 列表渲染 |
| Pinia/Vuex | Zustand/Redux | 狀態管理 |
| Vue Router | Next.js App Router | 路由 |
| Nuxt.js | Next.js | SSR 框架 |

#### 元件遷移範例（經銷存：商品列表）

```vue
<!-- Vue 3 - ProductList.vue -->
<template>
  <div class="product-list">
    <SearchBar v-model="searchQuery" @search="handleSearch" />
    <div v-if="loading" class="loading">載入中...</div>
    <table v-else>
      <tr v-for="product in filteredProducts" :key="product.id">
        <td>{{ product.code }}</td>
        <td>{{ product.name }}</td>
        <td>{{ formatCurrency(product.price) }}</td>
        <td>
          <span :class="stockClass(product.stock)">
            {{ product.stock }}
          </span>
        </td>
      </tr>
    </table>
    <Pagination :total="total" :page="page" @change="handlePageChange" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useProductStore } from '@/stores/product'

const store = useProductStore()
const searchQuery = ref('')
const page = ref(1)

const loading = computed(() => store.loading)
const filteredProducts = computed(() => store.products)
const total = computed(() => store.total)

const handleSearch = () => store.fetchProducts(searchQuery.value, page.value)
const handlePageChange = (p: number) => { page.value = p; handleSearch() }

onMounted(() => store.fetchProducts())
</script>
```

```tsx
// React (Next.js) - ProductList.tsx
'use client';

import { useState, useEffect, useMemo } from 'react';
import { useProductStore } from '@/stores/product';
import SearchBar from '@/components/SearchBar';
import Pagination from '@/components/Pagination';
import { formatCurrency, stockClass } from '@/utils/format';

export default function ProductList() {
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const { products, total, loading, fetchProducts } = useProductStore();

  useEffect(() => {
    fetchProducts();
  }, []);

  const handleSearch = () => fetchProducts(searchQuery, page);
  const handlePageChange = (p: number) => {
    setPage(p);
    fetchProducts(searchQuery, p);
  };

  return (
    <div className="product-list">
      <SearchBar
        value={searchQuery}
        onChange={setSearchQuery}
        onSearch={handleSearch}
      />
      {loading ? (
        <div className="loading">載入中...</div>
      ) : (
        <table>
          <tbody>
            {products.map(product => (
              <tr key={product.id}>
                <td>{product.code}</td>
                <td>{product.name}</td>
                <td>{formatCurrency(product.price)}</td>
                <td>
                  <span className={stockClass(product.stock)}>
                    {product.stock}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <Pagination total={total} page={page} onChange={handlePageChange} />
    </div>
  );
}
```

---

### 11.4 跨系統驗證技術

#### 資料一致性驗證腳本

```sql
-- 1. 逐表行數比對
-- Oracle 端
SELECT 'products' AS tbl, COUNT(*) AS cnt FROM products
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'inventory', COUNT(*) FROM inventory;

-- PostgreSQL 端（執行相同查詢，比對結果）

-- 2. 金額欄位加總比對
SELECT SUM(total_amount) AS order_total,
       SUM(tax_amount) AS tax_total,
       COUNT(*) AS order_count
FROM orders
WHERE order_date >= '2024-01-01';

-- 3. 抽樣明細比對（Hash 比對法）
-- Oracle
SELECT product_id,
       ORA_HASH(product_name || price || category) AS row_hash
FROM products
WHERE MOD(product_id, 100) = 0  -- 1% 抽樣
ORDER BY product_id;

-- PostgreSQL
SELECT product_id,
       MD5(product_name || price::text || category) AS row_hash
FROM products
WHERE product_id % 100 = 0
ORDER BY product_id;
```

#### API 功能對等驗證

```python
# 自動化 API 對等驗證腳本
import requests
import json
from deepdiff import DeepDiff

OLD_API = "http://old-python-api:8000"
NEW_API = "http://new-spring-api:8080"

test_cases = [
    ("GET", "/api/v1/products", {"page": 1, "size": 10}),
    ("GET", "/api/v1/products/123", {}),
    ("GET", "/api/v1/inventory?warehouse=WH001", {}),
    ("POST", "/api/v1/orders", {"items": [{"product_id": 1, "qty": 5}]}),
]

for method, path, params in test_cases:
    if method == "GET":
        old_resp = requests.get(f"{OLD_API}{path}", params=params)
        new_resp = requests.get(f"{NEW_API}{path}", params=params)
    else:
        old_resp = requests.post(f"{OLD_API}{path}", json=params)
        new_resp = requests.post(f"{NEW_API}{path}", json=params)

    diff = DeepDiff(
        old_resp.json(), new_resp.json(),
        ignore_order=True,
        exclude_paths=["root['timestamp']", "root['request_id']"]
    )

    status = "✅ PASS" if not diff else "❌ FAIL"
    print(f"{status} {method} {path}")
    if diff:
        print(f"  Diff: {json.dumps(diff, indent=2, default=str)}")
```

---

### 11.5 遷移案例: 經銷存管理系統全棧遷移

#### 背景

| 項目 | 內容 |
|------|------|
| **系統** | 經銷存管理系統（進貨/銷貨/庫存/報表） |
| **舊技術棧** | Vue 3 + Vite + TypeScript / Python FastAPI / Oracle 19c |
| **新技術棧** | React Next.js / Spring Boot 3 / PostgreSQL 18 |
| **新增平台** | Android（掃碼入出庫）、macOS（管理介面） |
| **資料量** | 50+ 表、300+ SP、100 萬+筆訂單、500 萬+筆庫存異動 |

#### 遷移時程（建議）

```
Week 1-2:  階段 1-2  現況分析 + 遷移架構設計
Week 3-6:  階段 3    DB 遷移 (Schema + SQL + SP + 資料)
Week 7-12: 階段 4    後端遷移 (Spring Boot 逐模組替換)
Week 13-20: 階段 5   前端遷移 (Next.js 逐頁面重寫)
Week 17-22: 階段 6   行動端開發 (Android 掃碼 + macOS)
Week 21-23: 階段 7   驗證與測試
Week 24-25: 階段 8   部署與切換
Week 26:   階段 9    知識沉澱
```

#### 關鍵風險與對策

| 風險 | 影響 | 對策 |
|------|------|------|
| Oracle 空字串=NULL 行為差異 | 業務邏輯錯誤 | 全面掃描 NVL/空字串相關代碼 |
| SP 業務邏輯遷移遺漏 | 功能缺失 | 建立 SP 清單，逐一標記遷移狀態 |
| 前端狀態管理差異 | UI 行為不一致 | Pinia→Zustand 逐 Store 遷移+比對 |
| 並行運行期間資料同步 | 資料不一致 | 單一 DB 策略，避免雙寫 |
| 行動端離線操作衝突 | 庫存數據錯誤 | Server-Wins + 衝突佇列通知 |

#### AISDLC Skill 啟用時機

```
階段 1: /sa-analyst → 需求重新分析
階段 2: /sd-architect → 遷移架構設計
階段 3: /database-migration → DB 遷移
        /integration-database → PostgreSQL 設定
階段 4: /dev-review → 後端程式碼審查
        /integration-api-client → API 客戶端建立
階段 5: /refactoring-code-quality → 前端程式碼品質
階段 6: /mobile-development → 行動端開發
階段 7: /testing-strategy → 測試策略
        /qa-testing → 驗收測試
階段 8: /devops-github-actions → CI/CD Pipeline
        /release-management → 版本發布
```

---

## 總結

本深度技術指南涵蓋了程式碼重構的完整主題:

✅ **代碼異味識別** - 系統化識別代碼問題
✅ **重構模式** - 深度解析常用重構技巧
✅ **大規模重構** - Mikado Method、並行變更策略
✅ **測試驅動重構** - TDR 循環和安全重構
✅ **設計模式重構** - 從程序式到物件導向
✅ **效能優化** - 演算法層級的重構
✅ **架構重構** - 分層架構和模組化
✅ **自動化工具** - IDE 和程式化重構工具
✅ **問題診斷** - 重構後問題排查和修復
✅ **真實案例** - Uber/Airbnb/Shopify 成功經驗
✅ **技術棧遷移** - DB遷移/後端遷移/前端遷移/跨系統驗證深度指南

---

**文檔版本: v0.01
**最後更新**: 2026-02-12
**維護者**: AISDLC Framework Team
