---
name: refactor
description: 執行代碼重構，改善代碼品質、降低複雜度、消除技術債
user-invocable: true
disable-model-invocation: false
argument-hint: "[scope: 重構範圍 (file/module/architecture)] [target: 目標檔案或模組路徑]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
  - Bash
---

# Refactoring Code Quality Skill

基於 AISDLC Refactoring 情境的代碼品質重構技能。

---

## 觸發方式

```bash
/refactor                           # 開始重構流程
/refactor file src/utils/helper.ts  # 重構指定檔案
/refactor module src/services/      # 重構整個模組
```

---

## 執行流程

### 階段 1: 重構評估 (10分鐘) 🔴

**任務**:
1. 識別重構目標
2. 分析現有代碼問題
3. 評估重構風險
4. 確認測試覆蓋率

**評估矩陣**:
| 問題類型 | 優先級 | 風險 | 建議方法 |
|---------|--------|------|---------|
| 高複雜度函數 | 🔴 高 | 中 | Extract Method |
| 重複代碼 | 🟡 中 | 低 | Extract Function |
| 過長類別 | 🔴 高 | 高 | Extract Class |
| 深層嵌套 | 🟡 中 | 低 | Guard Clause |
| 魔術數字 | ⚪ 低 | 低 | Extract Constant |

🔴 **確認點**: 確認重構範圍和預期目標

---

### 階段 2: 安全網建立

**關鍵步驟**:

#### 2.1 確保測試覆蓋
```bash
# 檢查現有測試
npm test -- --coverage

# 如果覆蓋率不足，先補充測試
```

**最低要求**:
- 重構區域覆蓋率 > 80%
- 關鍵路徑 100% 覆蓋

#### 2.2 建立基準測試
```typescript
// 記錄當前行為作為基準
describe('Refactoring Target - Baseline', () => {
  it('should maintain current behavior', () => {
    const result = targetFunction(input);
    expect(result).toMatchSnapshot();
  });
});
```

---

### 階段 3: 重構執行

**常用重構模式**:

#### Pattern 1: Extract Method (提取方法)

**Before**:
```typescript
function processOrder(order: Order) {
  // 驗證訂單
  if (!order.items || order.items.length === 0) {
    throw new Error('Empty order');
  }
  if (!order.customer) {
    throw new Error('No customer');
  }

  // 計算總價
  let total = 0;
  for (const item of order.items) {
    total += item.price * item.quantity;
  }

  // 套用折扣
  if (order.discount) {
    total = total * (1 - order.discount);
  }

  return { ...order, total };
}
```

**After**:
```typescript
function processOrder(order: Order) {
  validateOrder(order);
  const total = calculateTotal(order);
  return { ...order, total };
}

function validateOrder(order: Order): void {
  if (!order.items || order.items.length === 0) {
    throw new Error('Empty order');
  }
  if (!order.customer) {
    throw new Error('No customer');
  }
}

function calculateTotal(order: Order): number {
  const subtotal = order.items.reduce(
    (sum, item) => sum + item.price * item.quantity,
    0
  );
  return order.discount
    ? subtotal * (1 - order.discount)
    : subtotal;
}
```

#### Pattern 2: Replace Nested Conditional with Guard Clauses

**Before**:
```typescript
function getPayAmount(employee: Employee) {
  let result: number;
  if (employee.isSeparated) {
    result = separatedAmount();
  } else {
    if (employee.isRetired) {
      result = retiredAmount();
    } else {
      result = normalPayAmount();
    }
  }
  return result;
}
```

**After**:
```typescript
function getPayAmount(employee: Employee) {
  if (employee.isSeparated) return separatedAmount();
  if (employee.isRetired) return retiredAmount();
  return normalPayAmount();
}
```

#### Pattern 3: Replace Magic Numbers with Constants

**Before**:
```typescript
function calculateShipping(weight: number) {
  if (weight < 5) return weight * 2.5;
  if (weight < 20) return weight * 3.0;
  return weight * 3.5 + 10;
}
```

**After**:
```typescript
const SHIPPING_RATES = {
  LIGHT: { maxWeight: 5, rate: 2.5 },
  MEDIUM: { maxWeight: 20, rate: 3.0 },
  HEAVY: { rate: 3.5, surcharge: 10 },
} as const;

function calculateShipping(weight: number) {
  if (weight < SHIPPING_RATES.LIGHT.maxWeight) {
    return weight * SHIPPING_RATES.LIGHT.rate;
  }
  if (weight < SHIPPING_RATES.MEDIUM.maxWeight) {
    return weight * SHIPPING_RATES.MEDIUM.rate;
  }
  return weight * SHIPPING_RATES.HEAVY.rate + SHIPPING_RATES.HEAVY.surcharge;
}
```

---

### 階段 3B: Java/Spring Boot 重構範例

> 技術棧遷移涉及 Java 時使用

#### Pattern: Extract Service (提取服務層)

**Before** (Python Flask 單檔):
```python
@app.route('/orders', methods=['POST'])
def create_order():
    data = request.json
    if not data.get('items'):
        return jsonify(error='Empty order'), 400
    total = sum(i['price'] * i['qty'] for i in data['items'])
    if data.get('discount'):
        total *= (1 - data['discount'])
    db.execute("INSERT INTO orders ...", [total])
    return jsonify(total=total), 201
```

**After** (Spring Boot 分層):
```java
// OrderController.java
@RestController
@RequestMapping("/api/orders")
public class OrderController {
    private final OrderService orderService;

    @PostMapping
    public ResponseEntity<OrderResponse> createOrder(@Valid @RequestBody CreateOrderRequest request) {
        OrderResponse response = orderService.createOrder(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }
}

// OrderService.java
@Service
@Transactional
public class OrderService {
    private final OrderRepository orderRepository;

    public OrderResponse createOrder(CreateOrderRequest request) {
        BigDecimal total = calculateTotal(request.getItems());
        if (request.getDiscount() != null) {
            total = applyDiscount(total, request.getDiscount());
        }
        Order order = orderRepository.save(Order.of(request, total));
        return OrderResponse.from(order);
    }

    private BigDecimal calculateTotal(List<OrderItem> items) {
        return items.stream()
            .map(i -> i.getPrice().multiply(BigDecimal.valueOf(i.getQuantity())))
            .reduce(BigDecimal.ZERO, BigDecimal::add);
    }
}
```

#### 驗證命令 (Java/Spring Boot):
```bash
# 編譯
./gradlew compileJava

# 測試
./gradlew test

# Lint (Checkstyle/SpotBugs)
./gradlew check
```

---

### 階段 3C: Python 重構範例

> 舊系統 Python 代碼重構時使用

#### Pattern: Extract Class + Type Hints

**Before**:
```python
def process_inventory(data):
    results = []
    for item in data:
        if item['type'] == 'inbound':
            item['stock'] = item.get('stock', 0) + item['qty']
            if item['stock'] > item.get('max_stock', 9999):
                item['alert'] = 'overstock'
        elif item['type'] == 'outbound':
            item['stock'] = item.get('stock', 0) - item['qty']
            if item['stock'] < item.get('min_stock', 0):
                item['alert'] = 'understock'
        results.append(item)
    return results
```

**After**:
```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class TransactionType(Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"

@dataclass
class InventoryItem:
    sku: str
    stock: int = 0
    min_stock: int = 0
    max_stock: int = 9999
    alert: Optional[str] = None

    def apply_inbound(self, qty: int) -> None:
        self.stock += qty
        if self.stock > self.max_stock:
            self.alert = "overstock"

    def apply_outbound(self, qty: int) -> None:
        self.stock -= qty
        if self.stock < self.min_stock:
            self.alert = "understock"
```

#### 驗證命令 (Python):
```bash
# 型別檢查
mypy src/

# 測試
pytest --cov=src/

# Lint
ruff check src/
```

---

### 階段 4: 驗證 (必須執行)

**驗證步驟**:

```bash
# 1. 執行所有測試
npm test

# 2. 檢查類型
npx tsc --noEmit

# 3. 執行 Lint
npm run lint

# 4. 比對快照
npm test -- --updateSnapshot  # 如果行為改變
```

**驗證清單**:
- [ ] 所有測試通過
- [ ] 無類型錯誤
- [ ] Lint 無警告
- [ ] 行為與重構前一致

---

### 階段 5: 複雜度驗證

**重構前後比對**:

```markdown
## 重構成效報告

### 複雜度變化
| 函數 | 重構前 | 重構後 | 改善 |
|------|--------|--------|------|
| processOrder | 15 | 5 | ⬇️ 67% |
| validateOrder | - | 3 | 新增 |
| calculateTotal | - | 4 | 新增 |

### 代碼行數
- 重構前: 45 行
- 重構後: 35 行
- 淨減少: 22%

### 測試覆蓋率
- 重構前: 65%
- 重構後: 95%
```

---

## 重構原則

### DO（應該做）
- ✅ 小步快跑，每次只改一處
- ✅ 每次改動後執行測試
- ✅ 保持 Git commit 粒度小
- ✅ 使用 IDE 重構工具

### DON'T（不應該做）
- ❌ 同時重構多處
- ❌ 改變行為同時重構
- ❌ 在沒有測試下重構
- ❌ 一次性大規模改動

---

## 產出物清單

| 產出物 | 說明 |
|--------|------|
| 重構後代碼 | 改善後的代碼 |
| 重構報告 | 重構成效說明 |
| 更新的測試 | 新增或調整的測試 |

---

## 相關 Skill

- `/brownfield` - 系統分析（重構前置）
- `/testing` - 補充測試
- `/performance` - 效能優化

---


## 相關檔案

- SOP 參考: `scenarios/refactoring/SOP_QuickRef.md`

**基於**: AISDLC v0.09 Refactoring 情境
**維護者**: AISDLC Framework Team
