# 資料訪問層設計文件 (Data Access Layer Design Document)

**文檔類型**: 系統設計文件 (System Design Document)
**模板版本**: v1.0
**適用階段**: 階段 5 - 架構設計
**適用情境**: 本地 App（無 Backend API）
**對應 SOP**: Greenfield / Brownfield 情境
**建立日期**: YYYY-MM-DD
**AISDLC 版本**: v0.01+

---

## 📋 文檔元數據 (Document Metadata)

| 項目 | 內容 |
|------|------|
| **專案名稱** | [Project Name] |
| **專案代碼** | [Project Code] |
| **文檔版本** | v1.0 |
| **建立日期** | YYYY-MM-DD |
| **最後更新** | YYYY-MM-DD |
| **文檔狀態** | Draft / Review / Approved |
| **負責 SD-Architect** | Marcus (System Designer) |
| **參與人員** | [列出所有參與設計的人員] |
| **目標平台** | iOS / Android / Cross-platform Mobile |
| **資料庫類型** | Realm / SQLite / Core Data / Hive |

---

## 🎯 文檔目的 (Document Purpose)

本文檔針對**不需要 Backend API 的本地 App**（如純離線 Mobile App），設計資料訪問層架構，包括：
- 資料模型 (Data Model / Schema)
- Repository Pattern 定義
- Service Layer 設計
- 資料查詢方法
- 資料同步策略（如需要）
- 錯誤處理策略

**替代文件**: 對於需要 Backend API 的專案，請使用 `API_Specification_Template.md`

**使用者**: SD-Architect Agent、Dev Team、QA Team

---

## ⚠️ 使用時機判斷 (When to Use This Template)

### ✅ 應使用此模板的情境

- **純本地 Mobile App**: 所有資料存在本地資料庫（Realm, SQLite, CoreData）
- **單機應用**: 無需伺服器端計算或驗證
- **工具型 App**: 無需跨裝置資料同步
- **離線優先 App**: 100% 離線可用

**範例**:
- 記帳 App（本地版）
- 待辦事項 App（本地版）
- 筆記 App（本地版）
- 計算器 App
- 離線工具 App

---

### ❌ 不應使用此模板的情境

- **Web App 前後端分離**: 使用 `API_Specification_Template.md`
- **Mobile App 需雲端同步**: 使用 `API_Specification_Template.md` + 本模板（混合）
- **多平台共用資料**: 使用 `API_Specification_Template.md`
- **需伺服器端計算**: 使用 `API_Specification_Template.md`

---

## 1. 資料訪問層架構概述 (DAL Architecture Overview)

### 1.1 架構分層 (Architecture Layers)

```
┌──────────────────────────────────────────┐
│         Presentation Layer               │  ← UI Components (React Native / SwiftUI / Jetpack Compose)
│       (Screens, Components)              │
└──────────────────┬───────────────────────┘
                   │
┌──────────────────▼───────────────────────┐
│         Business Logic Layer             │  ← Services (業務邏輯層)
│  (TransactionService, CategoryService)   │
└──────────────────┬───────────────────────┘
                   │
┌──────────────────▼───────────────────────┐
│      Data Access Layer (本模板範圍)      │  ← Repositories (資料訪問層)
│  (TransactionRepo, CategoryRepo)         │
└──────────────────┬───────────────────────┘
                   │
┌──────────────────▼───────────────────────┐
│         Data Storage Layer               │  ← Database (Realm / SQLite / CoreData)
│      (Local Database)                    │
└──────────────────────────────────────────┘
```

---

### 1.2 設計模式 (Design Patterns)

**主要模式**: **Repository Pattern**

**定義**: Repository 作為資料存取的抽象層，封裝所有資料庫操作，提供乾淨的 API 給業務邏輯層。

**優點**:
- ✅ 關注點分離（Separation of Concerns）
- ✅ 易於測試（可 Mock Repository）
- ✅ 易於切換資料庫（如從 SQLite 切換到 Realm）
- ✅ 統一錯誤處理

**範例**:
```typescript
// ❌ 不好的做法：直接在 Component 中操作資料庫
function TransactionScreen() {
  const realm = useRealm();
  const transactions = realm.objects('Transaction'); // 緊耦合
  ...
}

// ✅ 好的做法：透過 Repository
function TransactionScreen() {
  const transactions = TransactionRepository.findAll(); // 解耦
  ...
}
```

---

## 2. 資料模型設計 (Data Model Design)

### 2.1 資料庫類型選擇

**本專案選擇**: [Realm / SQLite / Core Data / Hive]

**選擇理由**:
- [列出選擇此資料庫的理由]
- [參考 Tech_Stack_Selection_Report.md]

---

### 2.2 資料模型 Schema

**Schema 定義方法**:
- **Object Database (Realm, CoreData)**: 使用 Object Model Schema
- **關聯式資料庫 (SQLite)**: 使用 ER Diagram

---

#### 範例: Realm Object Model Schema (適用於 React Native + Realm)

**Transaction Schema**

```typescript
// src/database/schemas/Transaction.ts
import Realm from 'realm';

export class Transaction extends Realm.Object<Transaction> {
  _id!: Realm.BSON.ObjectId;
  amount!: number;
  type!: 'income' | 'expense';
  category!: Category;
  currency!: string;
  exchange_rate!: number; // 對台幣的匯率
  date!: Date;
  note?: string;
  photo_url?: string;
  created_at!: Date;
  updated_at!: Date;

  static schema: Realm.ObjectSchema = {
    name: 'Transaction',
    primaryKey: '_id',
    properties: {
      _id: { type: 'objectId', default: () => new Realm.BSON.ObjectId() },
      amount: 'double',
      type: 'string', // 'income' or 'expense'
      category: 'Category', // 關聯到 Category 物件
      currency: { type: 'string', default: 'TWD' },
      exchange_rate: { type: 'double', default: 1.0 },
      date: 'date',
      note: 'string?',
      photo_url: 'string?',
      created_at: { type: 'date', default: () => new Date() },
      updated_at: { type: 'date', default: () => new Date() }
    }
  };
}
```

**Category Schema**

```typescript
// src/database/schemas/Category.ts
import Realm from 'realm';

export class Category extends Realm.Object<Category> {
  _id!: Realm.BSON.ObjectId;
  name!: string;
  icon!: string;
  color!: string;
  type!: 'income' | 'expense';
  is_default!: boolean;
  created_at!: Date;

  // 反向關聯：此分類下的所有交易
  transactions!: Realm.List<Transaction>;

  static schema: Realm.ObjectSchema = {
    name: 'Category',
    primaryKey: '_id',
    properties: {
      _id: { type: 'objectId', default: () => new Realm.BSON.ObjectId() },
      name: 'string',
      icon: 'string',
      color: 'string',
      type: 'string', // 'income' or 'expense'
      is_default: { type: 'bool', default: false },
      created_at: { type: 'date', default: () => new Date() },
      // LinkingObjects: 反向查詢
      transactions: { type: 'linkingObjects', objectType: 'Transaction', property: 'category' }
    }
  };
}
```

**Budget Schema**

```typescript
// src/database/schemas/Budget.ts
import Realm from 'realm';

export class Budget extends Realm.Object<Budget> {
  _id!: Realm.BSON.ObjectId;
  category!: Category;
  amount!: number;
  month!: string; // 格式: 'YYYY-MM'
  created_at!: Date;

  static schema: Realm.ObjectSchema = {
    name: 'Budget',
    primaryKey: '_id',
    properties: {
      _id: { type: 'objectId', default: () => new Realm.BSON.ObjectId() },
      category: 'Category',
      amount: 'double',
      month: 'string',
      created_at: { type: 'date', default: () => new Date() }
    }
  };
}
```

---

#### 範例: SQLite ER Diagram (適用於關聯式資料庫)

```
┌──────────────────────────────────────────┐
│            transactions                   │
├──────────────────────────────────────────┤
│ id (PK)                INTEGER            │
│ amount                 REAL               │
│ type                   TEXT               │  ← 'income' or 'expense'
│ category_id (FK)       INTEGER            │
│ currency               TEXT               │
│ exchange_rate          REAL               │
│ date                   TEXT               │  ← ISO 8601 format
│ note                   TEXT               │
│ photo_url              TEXT               │
│ created_at             TEXT               │
│ updated_at             TEXT               │
└──────────────┬───────────────────────────┘
               │
               │ Many-to-One
               │
               ▼
┌──────────────────────────────────────────┐
│            categories                     │
├──────────────────────────────────────────┤
│ id (PK)                INTEGER            │
│ name                   TEXT               │
│ icon                   TEXT               │
│ color                  TEXT               │
│ type                   TEXT               │  ← 'income' or 'expense'
│ is_default             INTEGER            │  ← 0 or 1 (boolean)
│ created_at             TEXT               │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│              budgets                      │
├──────────────────────────────────────────┤
│ id (PK)                INTEGER            │
│ category_id (FK)       INTEGER            │
│ amount                 REAL               │
│ month                  TEXT               │  ← 'YYYY-MM'
│ created_at             TEXT               │
└──────────────┬───────────────────────────┘
               │
               │ Many-to-One
               │
               ▼
          categories
```

---

### 2.3 資料模型關係圖 (Entity Relationship Diagram)

**關係說明**:
- `Transaction` **Many-to-One** `Category`: 每筆交易屬於一個分類
- `Budget` **Many-to-One** `Category`: 每個預算設定屬於一個分類
- `Category` **One-to-Many** `Transaction`: 每個分類可有多筆交易（反向關聯）

**索引 (Indexes)**:
- `Transaction.date`: 加速日期範圍查詢
- `Transaction.category_id`: 加速分類查詢
- `Budget.month`: 加速月度預算查詢

---

## 3. Repository Pattern 定義 (Repository Pattern Definition)

### 3.1 Repository Interface 規範

**命名規則**: `[Entity]Repository`

**標準方法**:
- `create()`: 新增
- `findById()`: 依 ID 查詢
- `findAll()`: 查詢全部
- `update()`: 更新
- `delete()`: 刪除
- `[業務查詢方法]`: 依業務需求定義

---

### 3.2 TransactionRepository

```typescript
// src/database/repositories/TransactionRepository.ts
import { Transaction, Category } from '../schemas';
import Realm from 'realm';

export interface TransactionInput {
  amount: number;
  type: 'income' | 'expense';
  category_id: string; // Category ObjectId
  currency?: string;
  exchange_rate?: number;
  date: Date;
  note?: string;
  photo_url?: string;
}

export interface QueryOptions {
  limit?: number;
  offset?: number;
  sort?: {
    field: string;
    order: 'asc' | 'desc';
  };
}

export class TransactionRepository {
  private realm: Realm;

  constructor(realm: Realm) {
    this.realm = realm;
  }

  /**
   * 新增交易
   * @param input 交易資料
   * @returns 新增的交易物件
   */
  create(input: TransactionInput): Transaction {
    let transaction: Transaction;

    this.realm.write(() => {
      // 查詢分類
      const category = this.realm.objectForPrimaryKey<Category>('Category', new Realm.BSON.ObjectId(input.category_id));

      if (!category) {
        throw new Error(`Category not found: ${input.category_id}`);
      }

      // 建立交易
      transaction = this.realm.create<Transaction>('Transaction', {
        amount: input.amount,
        type: input.type,
        category: category,
        currency: input.currency || 'TWD',
        exchange_rate: input.exchange_rate || 1.0,
        date: input.date,
        note: input.note,
        photo_url: input.photo_url,
        created_at: new Date(),
        updated_at: new Date()
      });
    });

    return transaction!;
  }

  /**
   * 依 ID 查詢交易
   * @param id 交易 ID
   * @returns 交易物件或 null
   */
  findById(id: string): Transaction | null {
    return this.realm.objectForPrimaryKey<Transaction>('Transaction', new Realm.BSON.ObjectId(id));
  }

  /**
   * 查詢所有交易
   * @param options 查詢選項（分頁、排序）
   * @returns 交易陣列
   */
  findAll(options?: QueryOptions): Transaction[] {
    let results = this.realm.objects<Transaction>('Transaction');

    // 排序
    if (options?.sort) {
      const descending = options.sort.order === 'desc';
      results = results.sorted(options.sort.field, descending);
    } else {
      // 預設：依日期降序
      results = results.sorted('date', true);
    }

    // 分頁
    if (options?.limit) {
      const offset = options.offset || 0;
      return Array.from(results.slice(offset, offset + options.limit));
    }

    return Array.from(results);
  }

  /**
   * 更新交易
   * @param id 交易 ID
   * @param data 更新資料（部分欄位）
   * @returns 更新後的交易物件
   */
  update(id: string, data: Partial<TransactionInput>): Transaction {
    let transaction: Transaction | null;

    this.realm.write(() => {
      transaction = this.findById(id);

      if (!transaction) {
        throw new Error(`Transaction not found: ${id}`);
      }

      // 更新欄位
      if (data.amount !== undefined) transaction.amount = data.amount;
      if (data.type !== undefined) transaction.type = data.type;
      if (data.category_id !== undefined) {
        const category = this.realm.objectForPrimaryKey<Category>('Category', new Realm.BSON.ObjectId(data.category_id));
        if (category) transaction.category = category;
      }
      if (data.currency !== undefined) transaction.currency = data.currency;
      if (data.exchange_rate !== undefined) transaction.exchange_rate = data.exchange_rate;
      if (data.date !== undefined) transaction.date = data.date;
      if (data.note !== undefined) transaction.note = data.note;
      if (data.photo_url !== undefined) transaction.photo_url = data.photo_url;

      transaction.updated_at = new Date();
    });

    return transaction!;
  }

  /**
   * 刪除交易
   * @param id 交易 ID
   */
  delete(id: string): void {
    this.realm.write(() => {
      const transaction = this.findById(id);
      if (transaction) {
        this.realm.delete(transaction);
      }
    });
  }

  /**
   * 業務查詢方法：依日期範圍查詢交易
   * @param start 起始日期
   * @param end 結束日期
   * @returns 交易陣列
   */
  findByDateRange(start: Date, end: Date): Transaction[] {
    const results = this.realm.objects<Transaction>('Transaction')
      .filtered('date >= $0 AND date <= $1', start, end)
      .sorted('date', true);

    return Array.from(results);
  }

  /**
   * 業務查詢方法：依分類查詢交易
   * @param category_id 分類 ID
   * @returns 交易陣列
   */
  findByCategory(category_id: string): Transaction[] {
    const results = this.realm.objects<Transaction>('Transaction')
      .filtered('category._id == $0', new Realm.BSON.ObjectId(category_id))
      .sorted('date', true);

    return Array.from(results);
  }

  /**
   * 業務查詢方法：依類型查詢交易
   * @param type 交易類型（收入/支出）
   * @returns 交易陣列
   */
  findByType(type: 'income' | 'expense'): Transaction[] {
    const results = this.realm.objects<Transaction>('Transaction')
      .filtered('type == $0', type)
      .sorted('date', true);

    return Array.from(results);
  }

  /**
   * 業務查詢方法：計算月度總額
   * @param month 月份（格式: 'YYYY-MM'）
   * @param type 交易類型（收入/支出）
   * @returns 總額
   */
  calculateMonthlyTotal(month: string, type: 'income' | 'expense'): number {
    const [year, monthNum] = month.split('-').map(Number);
    const start = new Date(year, monthNum - 1, 1); // 月初
    const end = new Date(year, monthNum, 0, 23, 59, 59); // 月底

    const results = this.realm.objects<Transaction>('Transaction')
      .filtered('date >= $0 AND date <= $1 AND type == $2', start, end, type);

    // 計算總額（考慮匯率，統一換算為台幣）
    return results.reduce((sum, t) => sum + (t.amount * t.exchange_rate), 0);
  }
}
```

---

### 3.3 CategoryRepository

```typescript
// src/database/repositories/CategoryRepository.ts
import { Category } from '../schemas';
import Realm from 'realm';

export interface CategoryInput {
  name: string;
  icon: string;
  color: string;
  type: 'income' | 'expense';
  is_default?: boolean;
}

export class CategoryRepository {
  private realm: Realm;

  constructor(realm: Realm) {
    this.realm = realm;
  }

  /**
   * 新增分類
   */
  create(input: CategoryInput): Category {
    let category: Category;

    this.realm.write(() => {
      category = this.realm.create<Category>('Category', {
        name: input.name,
        icon: input.icon,
        color: input.color,
        type: input.type,
        is_default: input.is_default || false,
        created_at: new Date()
      });
    });

    return category!;
  }

  /**
   * 查詢所有分類
   */
  getAll(): Category[] {
    const results = this.realm.objects<Category>('Category').sorted('created_at');
    return Array.from(results);
  }

  /**
   * 查詢預設分類
   */
  getDefaults(): Category[] {
    const results = this.realm.objects<Category>('Category').filtered('is_default == true');
    return Array.from(results);
  }

  /**
   * 依類型查詢分類
   */
  getByType(type: 'income' | 'expense'): Category[] {
    const results = this.realm.objects<Category>('Category')
      .filtered('type == $0', type)
      .sorted('created_at');
    return Array.from(results);
  }

  /**
   * 更新分類
   */
  update(id: string, data: Partial<CategoryInput>): Category {
    let category: Category | null;

    this.realm.write(() => {
      category = this.realm.objectForPrimaryKey<Category>('Category', new Realm.BSON.ObjectId(id));

      if (!category) {
        throw new Error(`Category not found: ${id}`);
      }

      if (data.name !== undefined) category.name = data.name;
      if (data.icon !== undefined) category.icon = data.icon;
      if (data.color !== undefined) category.color = data.color;
      if (data.type !== undefined) category.type = data.type;
    });

    return category!;
  }

  /**
   * 刪除分類（需檢查是否有關聯交易）
   */
  delete(id: string): void {
    this.realm.write(() => {
      const category = this.realm.objectForPrimaryKey<Category>('Category', new Realm.BSON.ObjectId(id));

      if (!category) {
        throw new Error(`Category not found: ${id}`);
      }

      // 檢查是否有關聯交易
      if (category.transactions.length > 0) {
        throw new Error(`Cannot delete category: ${category.transactions.length} transactions associated`);
      }

      this.realm.delete(category);
    });
  }
}
```

---

## 4. Service Layer 設計 (Service Layer Design)

Service Layer 封裝業務邏輯，協調多個 Repository。

### 4.1 TransactionService

```typescript
// src/services/TransactionService.ts
import { TransactionRepository, CategoryRepository } from '../database/repositories';
import { Transaction } from '../database/schemas';

export class TransactionService {
  private transactionRepo: TransactionRepository;
  private categoryRepo: CategoryRepository;

  constructor(transactionRepo: TransactionRepository, categoryRepo: CategoryRepository) {
    this.transactionRepo = transactionRepo;
    this.categoryRepo = categoryRepo;
  }

  /**
   * 新增交易（含業務邏輯驗證）
   */
  async addTransaction(data: {
    amount: number;
    type: 'income' | 'expense';
    category_id: string;
    currency?: string;
    date: Date;
    note?: string;
    photo_url?: string;
  }): Promise<Transaction> {
    // 業務規則驗證
    if (data.amount <= 0) {
      throw new Error('Amount must be greater than 0');
    }

    // 驗證分類存在
    const category = this.categoryRepo.getAll().find(c => c._id.toString() === data.category_id);
    if (!category) {
      throw new Error('Category not found');
    }

    // 驗證分類類型與交易類型一致
    if (category.type !== data.type) {
      throw new Error(`Category type mismatch: expected ${data.type}, got ${category.type}`);
    }

    // 新增交易
    const transaction = this.transactionRepo.create(data);

    // 業務邏輯：檢查預算警示（如達到 80%）
    // await this.checkBudgetAlert(data.category_id, data.date);

    return transaction;
  }

  /**
   * 查詢月度摘要
   */
  getMonthlySummary(month: string): {
    income: number;
    expense: number;
    balance: number;
  } {
    const income = this.transactionRepo.calculateMonthlyTotal(month, 'income');
    const expense = this.transactionRepo.calculateMonthlyTotal(month, 'expense');

    return {
      income,
      expense,
      balance: income - expense
    };
  }

  /**
   * 查詢分類明細
   */
  getCategoryBreakdown(month: string, type: 'income' | 'expense'): Array<{
    category_name: string;
    amount: number;
    percentage: number;
  }> {
    // 實作分類統計邏輯
    // ...
    return [];
  }
}
```

---

### 4.2 StatisticsService

```typescript
// src/services/StatisticsService.ts
import { TransactionRepository } from '../database/repositories';

export interface MonthlySummary {
  month: string;
  income: number;
  expense: number;
  balance: number;
}

export interface CategoryBreakdown {
  category_id: string;
  category_name: string;
  amount: number;
  percentage: number;
  count: number;
}

export class StatisticsService {
  private transactionRepo: TransactionRepository;

  constructor(transactionRepo: TransactionRepository) {
    this.transactionRepo = transactionRepo;
  }

  /**
   * 取得月度摘要
   */
  getMonthlySummary(month: string): MonthlySummary {
    const income = this.transactionRepo.calculateMonthlyTotal(month, 'income');
    const expense = this.transactionRepo.calculateMonthlyTotal(month, 'expense');

    return {
      month,
      income,
      expense,
      balance: income - expense
    };
  }

  /**
   * 取得分類佔比
   */
  getCategoryBreakdown(month: string, type: 'income' | 'expense'): CategoryBreakdown[] {
    const [year, monthNum] = month.split('-').map(Number);
    const start = new Date(year, monthNum - 1, 1);
    const end = new Date(year, monthNum, 0, 23, 59, 59);

    const transactions = this.transactionRepo.findByDateRange(start, end)
      .filter(t => t.type === type);

    // 依分類分組統計
    const categoryMap = new Map<string, { name: string; amount: number; count: number }>();

    transactions.forEach(t => {
      const key = t.category._id.toString();
      const existing = categoryMap.get(key);
      const amount = t.amount * t.exchange_rate; // 統一換算為台幣

      if (existing) {
        existing.amount += amount;
        existing.count += 1;
      } else {
        categoryMap.set(key, {
          name: t.category.name,
          amount: amount,
          count: 1
        });
      }
    });

    // 計算總額
    const total = Array.from(categoryMap.values()).reduce((sum, item) => sum + item.amount, 0);

    // 轉換為陣列並計算百分比
    return Array.from(categoryMap.entries()).map(([id, data]) => ({
      category_id: id,
      category_name: data.name,
      amount: data.amount,
      percentage: total > 0 ? (data.amount / total) * 100 : 0,
      count: data.count
    })).sort((a, b) => b.amount - a.amount); // 依金額降序
  }

  /**
   * 取得月度趨勢（過去 N 個月）
   */
  getMonthlyTrend(months: number): MonthlySummary[] {
    const results: MonthlySummary[] = [];
    const now = new Date();

    for (let i = months - 1; i >= 0; i--) {
      const date = new Date(now.getFullYear(), now.getMonth() - i, 1);
      const month = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;

      results.push(this.getMonthlySummary(month));
    }

    return results;
  }
}
```

---

## 5. 資料初始化 (Data Initialization)

### 5.1 預設資料 (Seed Data)

首次啟動 App 時，建立預設分類：

```typescript
// src/database/seeds/categorySeed.ts
import { CategoryRepository } from '../repositories';

export const seedDefaultCategories = (categoryRepo: CategoryRepository) => {
  const defaultCategories = [
    // 支出分類
    { name: '食', icon: '🍔', color: '#FF6B6B', type: 'expense' as const, is_default: true },
    { name: '衣', icon: '👕', color: '#4ECDC4', type: 'expense' as const, is_default: true },
    { name: '住', icon: '🏠', color: '#45B7D1', type: 'expense' as const, is_default: true },
    { name: '行', icon: '🚗', color: '#FFA07A', type: 'expense' as const, is_default: true },
    { name: '育', icon: '📚', color: '#98D8C8', type: 'expense' as const, is_default: true },
    { name: '樂', icon: '🎮', color: '#F7DC6F', type: 'expense' as const, is_default: true },
    { name: '其他', icon: '📦', color: '#95A5A6', type: 'expense' as const, is_default: true },

    // 收入分類
    { name: '薪水', icon: '💰', color: '#52C41A', type: 'income' as const, is_default: true },
    { name: '獎金', icon: '🎁', color: '#1890FF', type: 'income' as const, is_default: true },
    { name: '投資', icon: '📈', color: '#722ED1', type: 'income' as const, is_default: true },
    { name: '其他收入', icon: '💵', color: '#13C2C2', type: 'income' as const, is_default: true },
  ];

  defaultCategories.forEach(cat => {
    try {
      categoryRepo.create(cat);
    } catch (error) {
      console.log(`Category ${cat.name} already exists, skipping...`);
    }
  });
};
```

---

## 6. 錯誤處理策略 (Error Handling Strategy)

### 6.1 錯誤類型定義

```typescript
// src/database/errors/DataAccessError.ts
export class DataAccessError extends Error {
  constructor(message: string, public originalError?: Error) {
    super(message);
    this.name = 'DataAccessError';
  }
}

export class ValidationError extends DataAccessError {
  constructor(message: string) {
    super(message);
    this.name = 'ValidationError';
  }
}

export class NotFoundError extends DataAccessError {
  constructor(entity: string, id: string) {
    super(`${entity} not found: ${id}`);
    this.name = 'NotFoundError';
  }
}

export class ConflictError extends DataAccessError {
  constructor(message: string) {
    super(message);
    this.name = 'ConflictError';
  }
}
```

---

### 6.2 錯誤處理範例

```typescript
// Repository 中的錯誤處理
try {
  const transaction = this.transactionRepo.create(data);
  return transaction;
} catch (error) {
  if (error instanceof NotFoundError) {
    // 處理找不到的情況
    console.error('Category not found:', error);
    throw new ValidationError('請選擇有效的分類');
  } else if (error instanceof ValidationError) {
    // 處理驗證錯誤
    throw error;
  } else {
    // 未知錯誤
    console.error('Unexpected error:', error);
    throw new DataAccessError('資料存取失敗，請稍後再試', error as Error);
  }
}
```

---

## 7. Schema 遷移策略 (Schema Migration Strategy)

### 7.1 版本控制

**Realm Schema 版本**:
```typescript
const realmConfig: Realm.Configuration = {
  schema: [Transaction, Category, Budget],
  schemaVersion: 2, // 每次 Schema 變更需遞增
  migration: (oldRealm, newRealm) => {
    // 遷移邏輯
  }
};
```

---

### 7.2 遷移範例

```typescript
// src/database/migrations/migration.ts
export const migrateRealmSchema = (oldRealm: Realm, newRealm: Realm, schemaVersion: number) => {
  // v0 → v1: 新增 exchange_rate 欄位
  if (oldRealm.schemaVersion < 1) {
    const oldObjects = oldRealm.objects('Transaction');
    const newObjects = newRealm.objects('Transaction');

    for (let i = 0; i < oldObjects.length; i++) {
      newObjects[i].exchange_rate = 1.0; // 預設值
    }
  }

  // v1 → v2: 新增 currency 欄位
  if (oldRealm.schemaVersion < 2) {
    const oldObjects = oldRealm.objects('Transaction');
    const newObjects = newRealm.objects('Transaction');

    for (let i = 0; i < oldObjects.length; i++) {
      newObjects[i].currency = 'TWD'; // 預設台幣
    }
  }
};
```

---

## 8. 效能優化建議 (Performance Optimization)

### 8.1 索引建立

- **高頻查詢欄位**：date, category_id, type
- **Realm 自動索引 primaryKey**

### 8.2 查詢優化

- 使用 `filtered()` 而非陣列 `filter()`
- 避免在 UI 主執行緒執行大量資料查詢
- 使用分頁（limit + offset）

### 8.3 記憶體管理

- 避免一次載入過多資料到記憶體
- 使用 Realm Results（lazy loading）

---

## 9. 測試策略 (Testing Strategy)

### 9.1 Repository 單元測試

```typescript
// __tests__/repositories/TransactionRepository.test.ts
import { TransactionRepository } from '../../src/database/repositories';
import Realm from 'realm';

describe('TransactionRepository', () => {
  let realm: Realm;
  let repo: TransactionRepository;

  beforeEach(() => {
    // 建立測試資料庫
    realm = new Realm({ inMemory: true, schema: [Transaction, Category] });
    repo = new TransactionRepository(realm);
  });

  afterEach(() => {
    realm.close();
  });

  it('should create a transaction', () => {
    const input = {
      amount: 100,
      type: 'expense' as const,
      category_id: 'test-category-id',
      date: new Date()
    };

    const transaction = repo.create(input);

    expect(transaction.amount).toBe(100);
    expect(transaction.type).toBe('expense');
  });

  // 更多測試案例...
});
```

---

## 10. 參考文件 (References)

1. [Tech_Stack_Selection_Report.md](../support/Tech_Stack_Selection_Report.md) - 技術選型報告
2. [FRD](../core/frd/FRD_[ProjectName].md) - 功能需求文件
3. [SRD_Template.md](./SRD_Template.md) - 系統需求文件
4. [Realm Documentation](https://www.mongodb.com/docs/realm/) - Realm 官方文檔
5. [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html) - Martin Fowler

---

**文檔建立時間**: YYYY-MM-DD HH:MM
**文檔路徑**: `docs_template/srd/Data_Access_Layer_Template.md`
**模板維護者**: AISDLC Framework Team
**模板狀態**: Active

---

**End of Data Access Layer Template**
