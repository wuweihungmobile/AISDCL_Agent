# Brownfield Project 舊專案維護與改造 - 深度技術指南
# Deep Dive Technical Guide

**版本**: v0.01
**最後更新**: 2026-02-15
**適用對象**: 經驗豐富的系統架構師、資深開發者、技術負責人
**建議閱讀**: 先閱讀 SOP_QuickRef.md 和 SOP.md
**文檔類型**: 技術參考、最佳實踐、深度分析

---

## 📚 文檔說明

### 何時閱讀此文檔

✅ **適合閱讀的情況**:
- 處理大型 Legacy 系統改造
- 面對嚴重技術債務需要系統性解決
- 需要制定長期重構策略
- 處理複雜的代碼依賴關係
- 無文檔或文檔過時的系統
- 需要進行架構現代化

❌ **不建議閱讀的情況**:
- 初次執行 Brownfield 專案(請閱讀 SOP.md)
- 快速參考流程(請閱讀 SOP_QuickRef.md)
- 簡單的 Bug 修復

### 文檔結構

```
Part 1: 代碼考古學 - 理解 Legacy 系統
Part 2: 技術債務評估與管理
Part 3: 安全重構策略
Part 3.5: 功能停用策略 (Deprecation) [v0.01 新增]
Part 4: 測試策略 - 為無測試系統添加保護網
Part 5: 資料庫遷移與 Schema 演進
Part 6: 依賴關係解耦
Part 7: 漸進式架構現代化
Part 7.5: 跨平台擴展與合規驅動變更 [v0.01 新增]
Part 8: 效能優化 - Legacy 系統特有問題
Part 9: 風險管理與回滾策略
Part 10: 真實案例研究
```

---

## Part 1: 代碼考古學 - 理解 Legacy 系統

### 1.1 代碼分析工具與技術

#### 靜態代碼分析工具

**JavaScript/TypeScript 生態**:

```bash
# ESLint - 代碼品質與潛在問題
npx eslint . --ext .js,.ts --format json > eslint-report.json

# SonarQube - 全面代碼品質分析
sonar-scanner \
  -Dsonar.projectKey=legacy-project \
  -Dsonar.sources=. \
  -Dsonar.host.url=http://localhost:9000

# Madge - 依賴關係視覺化
npx madge --circular --extensions js,ts src/
npx madge --image dependency-graph.svg src/

# Dependency Cruiser - 深度依賴分析
npx depcruise --exclude "^node_modules" --output-type dot src | dot -T svg > dependencies.svg
```

**Python 生態**:

```bash
# Pylint - 代碼品質檢查
pylint --output-format=json src/ > pylint-report.json

# Radon - 複雜度分析
radon cc src/ -a -nb  # 循環複雜度
radon mi src/ -nb     # 可維護性指數

# Bandit - 安全性掃描
bandit -r src/ -f json -o bandit-report.json

# Pyan - 調用圖生成
pyan *.py --uses --no-defines --colored --grouped --annotated --dot > callgraph.dot
```

**Java 生態**:

```bash
# PMD - 代碼品質檢查
pmd -d src/ -R rulesets/java/quickstart.xml -f text

# JDepend - 包依賴分析
jdepend -file jdepend-report.xml src/

# ArchUnit - 架構規則驗證
# (在測試中使用)

# JaCoCo - 代碼覆蓋率
mvn clean test jacoco:report
```

#### 動態分析與 Profiling

```javascript
// Node.js Profiling
// 1. CPU Profiling
node --prof app.js
node --prof-process isolate-*.log > processed.txt

// 2. Heap Snapshot
const v8 = require('v8');
const fs = require('fs');

function takeHeapSnapshot() {
  const snapshotStream = v8.writeHeapSnapshot();
  fs.copyFileSync(snapshotStream, `heap-${Date.now()}.heapsnapshot`);
}

// 3. 運行時監控
const { performance, PerformanceObserver } = require('perf_hooks');

const obs = new PerformanceObserver((items) => {
  items.getEntries().forEach((entry) => {
    console.log(`${entry.name}: ${entry.duration}ms`);
  });
});
obs.observe({ entryTypes: ['measure'] });

performance.mark('start-operation');
// ... 執行操作
performance.mark('end-operation');
performance.measure('operation', 'start-operation', 'end-operation');
```

### 1.2 理解代碼庫的系統方法

#### 建立心智模型的步驟

**Step 1: 識別系統邊界**

```bash
# 1. 找出所有對外接口
grep -r "app\.(get|post|put|delete)" --include="*.js" src/

# 2. 找出所有資料庫操作
grep -r "db\." --include="*.js" src/
grep -r "SELECT\|INSERT\|UPDATE\|DELETE" --include="*.sql" .

# 3. 找出所有外部 API 調用
grep -r "fetch\|axios\|http\." --include="*.js" src/

# 4. 找出所有環境變數
grep -r "process\.env\." --include="*.js" src/
```

**Step 2: 繪製系統架構圖**

```javascript
// 使用 dependency-cruiser 自動生成
// .dependency-cruiser.js
module.exports = {
  forbidden: [
    {
      name: 'no-circular',
      severity: 'error',
      from: {},
      to: {
        circular: true
      }
    },
    {
      name: 'no-deprecated-core',
      from: {},
      to: {
        dependencyTypes: ['core'],
        path: '^(punycode|domain|constants|sys|_linklist)$'
      }
    }
  ],
  options: {
    doNotFollow: {
      path: 'node_modules'
    },
    tsPreCompilationDeps: true,
    enhancedResolveOptions: {
      exportsFields: ["exports"],
      conditionNames: ["import", "require", "node", "default"]
    },
    reporterOptions: {
      archi: {
        collapsePattern: '^(src/[^/]+)',
        theme: {
          graph: {
            splines: 'ortho'
          }
        }
      }
    }
  }
};

// 執行
npx depcruise --config .dependency-cruiser.js --output-type archi src/
```

**Step 3: 識別核心業務邏輯**

```python
# Python 範例：使用 AST 分析
import ast
import os

class FunctionCallVisitor(ast.NodeVisitor):
    def __init__(self):
        self.calls = []

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self.calls.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            self.calls.append(f"{node.func.value.id}.{node.func.attr}")
        self.generic_visit(node)

def analyze_file(filepath):
    with open(filepath, 'r') as f:
        tree = ast.parse(f.read())

    visitor = FunctionCallVisitor()
    visitor.visit(tree)

    return visitor.calls

# 分析所有 Python 文件
for root, dirs, files in os.walk('src'):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            calls = analyze_file(filepath)
            print(f"{filepath}: {len(calls)} function calls")
```

### 1.3 文檔重建策略

**自動文檔生成**:

```javascript
// JSDoc 範例 - 為既有代碼添加文檔
/**
 * Processes user payment and updates order status
 * @param {string} userId - The user's unique identifier
 * @param {Object} paymentInfo - Payment information
 * @param {string} paymentInfo.method - Payment method (card/paypal/bank)
 * @param {number} paymentInfo.amount - Payment amount in cents
 * @returns {Promise<Object>} Payment result with transaction ID
 * @throws {PaymentError} When payment processing fails
 */
async function processPayment(userId, paymentInfo) {
  // 既有代碼
}

// 生成文檔
npx jsdoc -c jsdoc.json -r src/
```

**使用 AI 輔助理解代碼**:

```python
# 使用 OpenAI API 生成代碼解釋
import openai

def explain_code(code_snippet):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a code analyst. Explain what the following code does, identify potential issues, and suggest improvements."},
            {"role": "user", "content": code_snippet}
        ]
    )
    return response.choices[0].message.content

# 範例使用
legacy_code = """
function processOrder(order) {
  var total = 0;
  for (var i = 0; i < order.items.length; i++) {
    total += order.items[i].price * order.items[i].qty;
  }
  if (order.discount) total = total - order.discount;
  return total;
}
"""

explanation = explain_code(legacy_code)
print(explanation)
```

---

## Part 2: 技術債務評估與管理

### 2.1 技術債務量化框架

#### SQALE 方法 (Software Quality Assessment based on Lifecycle Expectations)

```yaml
技術債務計算公式:

Technical Debt Ratio (TDR) =
  (Remediation Cost / Development Cost) × 100%

評級標準:
  A: TDR ≤ 5%    (優秀)
  B: TDR ≤ 10%   (良好)
  C: TDR ≤ 20%   (普通)
  D: TDR ≤ 50%   (待改善)
  E: TDR > 50%   (嚴重)

Remediation Cost 計算:
  - Code Smells: 每個 2-30 分鐘
  - Bugs: 每個 5-60 分鐘
  - Vulnerabilities: 每個 15-120 分鐘
  - Duplications: 依照重複行數計算
```

**實作範例**:

```javascript
// 使用 SonarQube API 獲取技術債務數據
const axios = require('axios');

async function getTechnicalDebt(projectKey) {
  const baseUrl = 'http://localhost:9000/api';

  // 獲取技術債務指標
  const measures = await axios.get(`${baseUrl}/measures/component`, {
    params: {
      component: projectKey,
      metricKeys: 'sqale_index,sqale_rating,reliability_rating,security_rating,code_smells,bugs,vulnerabilities'
    }
  });

  const metrics = measures.data.component.measures.reduce((acc, m) => {
    acc[m.metric] = m.value;
    return acc;
  }, {});

  // sqale_index 是以分鐘為單位的技術債務
  const debtHours = parseInt(metrics.sqale_index) / 60;
  const debtDays = debtHours / 8;

  return {
    debtDays: debtDays.toFixed(2),
    rating: metrics.sqale_rating,
    codeSmells: metrics.code_smells,
    bugs: metrics.bugs,
    vulnerabilities: metrics.vulnerabilities,
    reliability: metrics.reliability_rating,
    security: metrics.security_rating
  };
}

// 使用
getTechnicalDebt('my-legacy-project').then(debt => {
  console.log(`技術債務: ${debt.debtDays} 天`);
  console.log(`維護性評級: ${debt.rating}`);
  console.log(`Code Smells: ${debt.codeSmells}`);
  console.log(`Bugs: ${debt.bugs}`);
  console.log(`安全漏洞: ${debt.vulnerabilities}`);
});
```

### 2.1.1 AISDLC 技術債評分公式

> 📌 **SOP 參考**: 完整定義見 [SOP.md](./SOP.md) 步驟 2.3

```yaml
AISDLC TD_Score 公式:
  TD_Score = (Complexity × Coupling × Age_Factor) / Test_Coverage

解讀標準 (5 級):
  0-5 分:   🟢 技術債可控 - 正常維護
  5-10 分:  🟡 需要關注 - 建議安排技術債清償
  10-16 分: 🟠 技術債累積 - 建議在本次變更中一併處理
  16-50 分: 🔴 嚴重技術債 - 必須在本次變更中優先處理
  >50 分:   ⚫ 極度危險 - 建議暫停功能開發，全力清償技術債

注意: TD_Score > 100 以 100 計算（上限）
```

### 2.2 技術債務優先級矩陣

```yaml
優先級評估維度:

1. 影響範圍 (Impact)
   - Critical: 影響核心業務流程
   - High: 影響主要功能
   - Medium: 影響次要功能
   - Low: 影響邊緣功能

2. 修復難度 (Effort)
   - Easy: < 1 天
   - Medium: 1-5 天
   - Hard: 5-15 天
   - Very Hard: > 15 天

3. 風險等級 (Risk)
   - High: 可能造成系統故障或資料損失
   - Medium: 可能造成功能異常
   - Low: 不影響系統運作

優先級矩陣:

           │ Easy  │ Medium │ Hard  │ V.Hard
───────────┼───────┼────────┼───────┼────────
Critical   │  P1   │   P1   │  P2   │   P2
High       │  P1   │   P2   │  P2   │   P3
Medium     │  P2   │   P2   │  P3   │   P4
Low        │  P3   │   P3   │  P4   │   P4

P1: 立即處理 (本 Sprint)
P2: 短期處理 (1-2 Sprints)
P3: 中期處理 (計劃中)
P4: 長期處理 (Backlog)
```

**實作工具**:

```javascript
// 技術債務追蹤系統
class TechnicalDebtItem {
  constructor(data) {
    this.id = data.id;
    this.title = data.title;
    this.description = data.description;
    this.impact = data.impact; // 'critical' | 'high' | 'medium' | 'low'
    this.effort = data.effort; // 'easy' | 'medium' | 'hard' | 'very-hard'
    this.risk = data.risk; // 'high' | 'medium' | 'low'
    this.affectedModules = data.affectedModules || [];
    this.estimatedCost = data.estimatedCost; // 以小時計
  }

  calculatePriority() {
    const priorityMatrix = {
      'critical-easy': 'P1',
      'critical-medium': 'P1',
      'critical-hard': 'P2',
      'critical-very-hard': 'P2',
      'high-easy': 'P1',
      'high-medium': 'P2',
      'high-hard': 'P2',
      'high-very-hard': 'P3',
      'medium-easy': 'P2',
      'medium-medium': 'P2',
      'medium-hard': 'P3',
      'medium-very-hard': 'P4',
      'low-easy': 'P3',
      'low-medium': 'P3',
      'low-hard': 'P4',
      'low-very-hard': 'P4'
    };

    const key = `${this.impact}-${this.effort}`;
    return priorityMatrix[key] || 'P4';
  }

  getROI() {
    // ROI = 影響範圍 / 修復成本
    const impactScore = {
      'critical': 100,
      'high': 50,
      'medium': 20,
      'low': 5
    };

    return (impactScore[this.impact] || 0) / this.estimatedCost;
  }
}

// 使用範例
const debtItems = [
  new TechnicalDebtItem({
    id: 'TD-001',
    title: '用戶認證邏輯存在 SQL Injection 風險',
    impact: 'critical',
    effort: 'medium',
    risk: 'high',
    estimatedCost: 16
  }),
  new TechnicalDebtItem({
    id: 'TD-002',
    title: '訂單處理函數循環複雜度過高 (CC=42)',
    impact: 'high',
    effort: 'hard',
    risk: 'medium',
    estimatedCost: 40
  })
];

// 按優先級和 ROI 排序
debtItems.sort((a, b) => {
  const priorityOrder = { 'P1': 1, 'P2': 2, 'P3': 3, 'P4': 4 };
  const priorityDiff = priorityOrder[a.calculatePriority()] - priorityOrder[b.calculatePriority()];

  if (priorityDiff !== 0) return priorityDiff;

  // 相同優先級時,按 ROI 排序
  return b.getROI() - a.getROI();
});

console.log('技術債務處理順序:');
debtItems.forEach(item => {
  console.log(`${item.calculatePriority()} - ${item.title} (ROI: ${item.getROI().toFixed(2)})`);
});
```

---

## Part 3: 安全重構策略

### 3.1 Strangler Fig Pattern (絞殺者模式)

**概念**: 逐步用新系統替換舊系統,而非大爆炸式重寫。

```yaml
實施步驟:

1. 建立 Facade (門面)
   在舊系統前建立一層代理,所有請求先經過 Facade

2. 識別可獨立的功能模組
   選擇邊界清晰、依賴少的模組優先遷移

3. 在 Facade 中實作路由邏輯
   根據條件將請求導向新系統或舊系統

4. 漸進式遷移
   一個模組一個模組遷移,確保每次都可正常運作

5. 最終淘汰舊系統
   當所有功能都遷移完成後,移除舊系統
```

**實作範例**:

```javascript
// 使用 Express 實作 Strangler Facade
const express = require('express');
const httpProxy = require('http-proxy');

const app = express();
const legacyProxy = httpProxy.createProxyServer({ target: 'http://legacy-system:8080' });
const newSystemProxy = httpProxy.createProxyServer({ target: 'http://new-system:3000' });

// Feature Toggle 配置
const featureToggles = {
  'new-auth': { enabled: true, rollout: 100 }, // 100% 流量到新系統
  'new-payment': { enabled: true, rollout: 50 }, // 50% 流量到新系統
  'new-orders': { enabled: false, rollout: 0 }  // 0% 流量到新系統
};

// 決定路由到新系統或舊系統
function shouldUseNewSystem(feature, userId) {
  const toggle = featureToggles[feature];

  if (!toggle || !toggle.enabled) {
    return false;
  }

  // 基於用戶 ID 的一致性 Hash (確保同一用戶總是路由到相同系統)
  if (toggle.rollout === 100) {
    return true;
  }

  const hash = userId.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return (hash % 100) < toggle.rollout;
}

// 路由中介軟體
app.use('/api/auth/*', (req, res) => {
  const userId = req.headers['x-user-id'] || 'anonymous';

  if (shouldUseNewSystem('new-auth', userId)) {
    console.log(`Routing /api/auth to NEW system for user ${userId}`);
    newSystemProxy.web(req, res);
  } else {
    console.log(`Routing /api/auth to LEGACY system for user ${userId}`);
    legacyProxy.web(req, res);
  }
});

app.use('/api/payments/*', (req, res) => {
  const userId = req.headers['x-user-id'] || 'anonymous';

  if (shouldUseNewSystem('new-payment', userId)) {
    newSystemProxy.web(req, res);
  } else {
    legacyProxy.web(req, res);
  }
});

// 預設：所有其他請求路由到舊系統
app.use('*', (req, res) => {
  legacyProxy.web(req, res);
});

app.listen(80, () => {
  console.log('Strangler Facade running on port 80');
});
```

### 3.2 Branch by Abstraction (抽象分支)

**適用場景**: 無法停止開發的情況下進行大規模重構。

```javascript
// Step 1: 建立抽象層
// 舊代碼直接使用 MySQL
// const mysql = require('mysql');
// const connection = mysql.createConnection({ ... });

// 新建抽象層
class DatabaseAbstraction {
  constructor(implementation) {
    this.db = implementation;
  }

  async query(sql, params) {
    return this.db.query(sql, params);
  }

  async findOne(table, conditions) {
    return this.db.findOne(table, conditions);
  }

  async insert(table, data) {
    return this.db.insert(table, data);
  }
}

// Step 2: 實作舊版本 (MySQL)
class MySQLImplementation {
  constructor(connection) {
    this.connection = connection;
  }

  async query(sql, params) {
    return new Promise((resolve, reject) => {
      this.connection.query(sql, params, (err, results) => {
        if (err) reject(err);
        else resolve(results);
      });
    });
  }

  async findOne(table, conditions) {
    const where = Object.keys(conditions)
      .map(key => `${key} = ?`)
      .join(' AND ');
    const values = Object.values(conditions);

    const sql = `SELECT * FROM ${table} WHERE ${where} LIMIT 1`;
    const results = await this.query(sql, values);
    return results[0];
  }

  async insert(table, data) {
    const columns = Object.keys(data).join(', ');
    const placeholders = Object.keys(data).map(() => '?').join(', ');
    const values = Object.values(data);

    const sql = `INSERT INTO ${table} (${columns}) VALUES (${placeholders})`;
    const result = await this.query(sql, values);
    return result.insertId;
  }
}

// Step 3: 實作新版本 (PostgreSQL with Knex)
class PostgreSQLImplementation {
  constructor(knex) {
    this.knex = knex;
  }

  async query(sql, params) {
    return this.knex.raw(sql, params);
  }

  async findOne(table, conditions) {
    return this.knex(table).where(conditions).first();
  }

  async insert(table, data) {
    const [id] = await this.knex(table).insert(data).returning('id');
    return id;
  }
}

// Step 4: 使用 Feature Toggle 切換實作
const useNewDatabase = process.env.USE_POSTGRESQL === 'true';

let dbImplementation;
if (useNewDatabase) {
  const knex = require('knex')({ /* config */ });
  dbImplementation = new PostgreSQLImplementation(knex);
} else {
  const mysql = require('mysql');
  const connection = mysql.createConnection({ /* config */ });
  dbImplementation = new MySQLImplementation(connection);
}

const db = new DatabaseAbstraction(dbImplementation);

// Step 5: 應用代碼使用抽象層
async function getUser(userId) {
  return db.findOne('users', { id: userId });
}

async function createUser(userData) {
  return db.insert('users', userData);
}

// Step 6: 漸進式遷移
// 1. 先在測試環境使用新實作
// 2. 使用 Canary 部署在 5% 流量測試
// 3. 逐步增加到 100%
// 4. 移除舊實作和 Feature Toggle
```

### 3.3 Parallel Change (並行變更)

**也稱為 Expand-Contract Pattern**

```yaml
三階段重構:

Phase 1: Expand (擴展)
  - 在保留舊 API 的同時,新增新 API
  - 新舊 API 同時運作

Phase 2: Migrate (遷移)
  - 逐步將調用方從舊 API 遷移到新 API
  - 監控新 API 的穩定性

Phase 3: Contract (收縮)
  - 移除舊 API
  - 清理相關代碼
```

**實作範例**:

```javascript
// ===== Phase 1: Expand =====

// 舊 API (保留)
app.get('/api/users/:id', async (req, res) => {
  const user = await db.query('SELECT * FROM users WHERE id = ?', [req.params.id]);

  // 舊格式
  res.json({
    id: user.id,
    name: user.name,
    email: user.email
  });
});

// 新 API (新增)
app.get('/api/v2/users/:id', async (req, res) => {
  const user = await db.query('SELECT * FROM users WHERE id = ?', [req.params.id]);

  // 新格式 (RESTful, 包含更多資訊)
  res.json({
    data: {
      id: user.id,
      type: 'user',
      attributes: {
        name: user.name,
        email: user.email,
        createdAt: user.created_at,
        updatedAt: user.updated_at
      },
      relationships: {
        orders: {
          links: {
            related: `/api/v2/users/${user.id}/orders`
          }
        }
      }
    },
    links: {
      self: `/api/v2/users/${user.id}`
    }
  });
});

// ===== Phase 2: Migrate =====

// 前端逐步遷移
// 舊代碼
async function fetchUser(userId) {
  const response = await fetch(`/api/users/${userId}`);
  return response.json();
}

// 新代碼 (使用 Feature Toggle)
const USE_V2_API = window.featureFlags?.useV2API || false;

async function fetchUser(userId) {
  const endpoint = USE_V2_API
    ? `/api/v2/users/${userId}`
    : `/api/users/${userId}`;

  const response = await fetch(endpoint);
  const data = await response.json();

  // 統一格式化為新格式
  if (!USE_V2_API) {
    // 轉換舊格式到新格式
    return {
      data: {
        id: data.id,
        type: 'user',
        attributes: {
          name: data.name,
          email: data.email
        }
      }
    };
  }

  return data;
}

// ===== Phase 3: Contract =====

// 監控舊 API 使用量
const deprecatedEndpoints = new Map();

app.get('/api/users/:id', async (req, res) => {
  // 記錄使用量
  const count = deprecatedEndpoints.get('/api/users/:id') || 0;
  deprecatedEndpoints.set('/api/users/:id', count + 1);

  // 添加 Deprecation Header
  res.set('Deprecation', 'true');
  res.set('Sunset', 'Sat, 31 Dec 2024 23:59:59 GMT');
  res.set('Link', '</api/v2/users/:id>; rel="alternate"');

  // ... 原有邏輯
});

// 當舊 API 使用量降至 0 後,移除
// app.get('/api/users/:id', ...) // 刪除此路由
```

---

## Part 3.5: 功能停用策略 (Deprecation) [v0.01 新增]

> 📌 **SOP 參考**: 完整流程見 [SOP.md](./SOP.md) 情境 E

### 3.5.1 漸進式停用 7 步策略

```yaml
功能停用黃金步驟:

Step 1: 停用影響分析
  - 識別所有使用該功能的模組和使用者
  - 計算影響範圍（內部呼叫者、外部 API 消費者、UI 入口）
  - 評估資料依賴

Step 2: 替代方案準備
  - 新功能或替代方案就緒
  - 遷移路徑文檔化
  - 使用者通知計畫

Step 3: 標記為 Deprecated
  - 代碼標記: @Deprecated / @deprecated
  - API 回應加入 Deprecation Header
  - 文檔標註停用時間表

Step 4: 監控使用量
  - 追蹤 Deprecated 功能呼叫次數
  - 識別仍在使用的消費者
  - 提供遷移協助

Step 5: 限制新使用
  - 防止新代碼呼叫 Deprecated 功能
  - CI/CD 加入 Deprecated 使用警告

Step 6: 最終移除
  - 使用量降至 0 後移除代碼
  - 清理相關資料庫 Schema（如需要）

Step 7: 驗證
  - 確認移除後無副作用
  - 更新所有相關文檔
```

### 3.5.2 停用檢查清單

```yaml
功能停用前:
  □ 影響範圍已完整分析
  □ 替代方案已就緒並經過測試
  □ 遷移文檔已撰寫
  □ 使用者已通知（含時間表）
  □ 資料遷移/歸檔策略已確認

停用執行中:
  □ Deprecated 標記已加入
  □ 監控機制已部署
  □ 使用量趨勢持續下降

停用完成後:
  □ 代碼已完全移除
  □ 資料庫 Schema 已清理
  □ 文檔已更新
  □ 回歸測試通過
```

---

## Part 4: 測試策略 - 為無測試系統添加保護網

### 4.1 特性測試 (Characterization Tests)

**目的**: 記錄現有系統的行為,而非驗證正確性。

```javascript
// 範例：為既有函數添加特性測試
// 既有代碼 (無文檔、不確定行為)
function calculateDiscount(order) {
  let discount = 0;
  if (order.total > 1000) discount = order.total * 0.1;
  if (order.customer.vip) discount += 50;
  if (order.items.length > 5) discount += order.total * 0.05;
  return Math.min(discount, order.total * 0.3);
}

// 特性測試：記錄實際行為
describe('calculateDiscount - Characterization Tests', () => {
  it('should return 0 for orders under 1000', () => {
    const order = {
      total: 500,
      customer: { vip: false },
      items: [{}, {}]
    };

    expect(calculateDiscount(order)).toBe(0);
  });

  it('should return 10% for orders over 1000', () => {
    const order = {
      total: 1500,
      customer: { vip: false },
      items: [{}, {}]
    };

    expect(calculateDiscount(order)).toBe(150);
  });

  it('should add 50 for VIP customers', () => {
    const order = {
      total: 500,
      customer: { vip: true },
      items: [{}, {}]
    };

    expect(calculateDiscount(order)).toBe(50);
  });

  it('should add 5% for orders with more than 5 items', () => {
    const order = {
      total: 1000,
      customer: { vip: false },
      items: [{}, {}, {}, {}, {}, {}] // 6 items
    };

    // 10% (100) + 5% (50) = 150
    expect(calculateDiscount(order)).toBe(150);
  });

  it('should cap discount at 30% of total', () => {
    const order = {
      total: 2000,
      customer: { vip: true },
      items: [{}, {}, {}, {}, {}, {}]
    };

    // 10% (200) + 50 + 5% (100) = 350
    // 但最多 30% (600), 所以是 350
    expect(calculateDiscount(order)).toBe(350);
  });

  it('should handle edge case: max discount limit', () => {
    const order = {
      total: 1000,
      customer: { vip: true },
      items: Array(10).fill({})
    };

    // 10% (100) + 50 + 5% (50) = 200
    // 但最多 30% (300), 所以是 200
    expect(calculateDiscount(order)).toBe(200);
  });
});
```

### 4.2 Golden Master Testing (黃金樣本測試)

**適用**: 複雜的數據轉換、報表生成等。

```python
# Python 範例
import json
import hashlib
import unittest

class GoldenMasterTest(unittest.TestCase):
    def setUp(self):
        # 準備測試數據
        self.input_data = {
            'orders': [
                {'id': 1, 'total': 100, 'items': [...]},
                {'id': 2, 'total': 200, 'items': [...]}
            ],
            'date_range': {'start': '2024-01-01', 'end': '2024-01-31'}
        }

    def test_report_generation_golden_master(self):
        # 執行既有函數
        from legacy_system import generate_monthly_report
        result = generate_monthly_report(self.input_data)

        # 將結果序列化並計算 hash
        result_json = json.dumps(result, sort_keys=True, indent=2)
        result_hash = hashlib.sha256(result_json.encode()).hexdigest()

        # 第一次執行時,儲存為 golden master
        golden_file = 'tests/golden_masters/monthly_report.json'
        golden_hash_file = 'tests/golden_masters/monthly_report.sha256'

        # 讀取 golden master
        try:
            with open(golden_file, 'r') as f:
                golden_master = f.read()
            with open(golden_hash_file, 'r') as f:
                golden_hash = f.read().strip()
        except FileNotFoundError:
            # 第一次執行:儲存 golden master
            with open(golden_file, 'w') as f:
                f.write(result_json)
            with open(golden_hash_file, 'w') as f:
                f.write(result_hash)

            self.fail("Golden master created. Please review and commit.")

        # 比較 hash
        if result_hash != golden_hash:
            # Hash 不符:儲存差異
            with open('tests/golden_masters/monthly_report.diff.json', 'w') as f:
                f.write(result_json)

            self.fail(f"Output differs from golden master!\n"
                     f"Expected hash: {golden_hash}\n"
                     f"Actual hash: {result_hash}\n"
                     f"Diff saved to: tests/golden_masters/monthly_report.diff.json")
```

### 4.3 測試覆蓋率漸進式提升策略

```yaml
階段式提升測試覆蓋率:

Phase 1: 建立基線 (0% → 20%)
  目標: 核心業務邏輯和高風險區域
  方法:
    - 識別最常變更的文件 (git log --follow)
    - 為關鍵業務函數添加特性測試
    - 為已知 Bug 區域添加回歸測試

Phase 2: 擴展覆蓋 (20% → 50%)
  目標: 所有 API 端點和主要功能
  方法:
    - 為每個 API 端點添加集成測試
    - 為數據模型添加單元測試
    - 為工具函數添加單元測試

Phase 3: 全面覆蓋 (50% → 80%)
  目標: 所有公開函數和邊界情況
  方法:
    - 為所有公開函數添加測試
    - 添加邊界條件測試
    - 添加錯誤處理測試

Phase 4: 精細化 (80%+)
  目標: 達到可接受的覆蓋率
  方法:
    - 使用 Mutation Testing 驗證測試品質
    - 添加效能測試
    - 添加安全性測試
```

**自動化測試覆蓋率監控**:

```javascript
// package.json
{
  "scripts": {
    "test": "jest --coverage",
    "test:watch": "jest --watch",
    "test:coverage-threshold": "jest --coverage --coverageThreshold='{\"global\":{\"branches\":50,\"functions\":50,\"lines\":50,\"statements\":50}}'"
  }
}

// jest.config.js
module.exports = {
  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/*.stories.{js,jsx,ts,tsx}',
    '!src/**/__tests__/**'
  ],
  coverageThreshold: {
    global: {
      branches: 50,
      functions: 50,
      lines: 50,
      statements: 50
    },
    // 對核心模組要求更高覆蓋率
    './src/core/': {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    }
  },
  coverageReporters: ['text', 'lcov', 'html']
};

// CI/CD 中檢查覆蓋率趨勢
// .github/workflows/ci.yml
- name: Check coverage trend
  run: |
    npm test -- --coverage --coverageReporters=json-summary
    COVERAGE=$(node -p "require('./coverage/coverage-summary.json').total.lines.pct")
    echo "Current coverage: $COVERAGE%"

    if (( $(echo "$COVERAGE < 50" | bc -l) )); then
      echo "::error::Coverage is below 50%"
      exit 1
    fi
```

---

## Part 5: 資料庫遷移與 Schema 演進

### 5.1 零停機時間資料庫遷移

**策略: Expand-Migrate-Contract**

```sql
-- ===== Phase 1: Expand =====
-- 新增新欄位,但保留舊欄位

-- 舊 Schema
CREATE TABLE users (
  id INT PRIMARY KEY,
  name VARCHAR(255),
  address TEXT  -- 舊欄位:單一地址字串
);

-- Expand: 新增新欄位
ALTER TABLE users ADD COLUMN address_json JSONB;

-- ===== Phase 2: Migrate =====
-- 雙寫策略:同時寫入舊欄位和新欄位

-- 應用代碼
async function updateUserAddress(userId, addressData) {
  const addressString = `${addressData.street}, ${addressData.city}`;
  const addressJSON = JSON.stringify(addressData);

  await db.query(
    `UPDATE users
     SET address = $1, address_json = $2
     WHERE id = $3`,
    [addressString, addressJSON, userId]
  );
}

-- 背景任務:遷移既有資料
-- migration script
UPDATE users
SET address_json = json_build_object(
  'street', split_part(address, ',', 1),
  'city', trim(split_part(address, ',', 2))
)
WHERE address_json IS NULL AND address IS NOT NULL;

-- 驗證遷移
SELECT COUNT(*)
FROM users
WHERE address IS NOT NULL AND address_json IS NULL;
-- 應該返回 0

-- ===== Phase 3: Contract =====
-- 移除舊欄位

-- 首先,停止寫入舊欄位
async function updateUserAddress(userId, addressData) {
  const addressJSON = JSON.stringify(addressData);

  await db.query(
    `UPDATE users
     SET address_json = $1
     WHERE id = $2`,
    [addressJSON, userId]
  );
}

-- 確認沒有任何代碼讀取舊欄位後,移除
ALTER TABLE users DROP COLUMN address;
```

### 5.2 大型資料表遷移策略

```sql
-- 問題:修改大型資料表 (億級記錄) 會鎖表

-- ❌ 錯誤做法:直接 ALTER TABLE (會鎖表數小時)
ALTER TABLE large_table ADD COLUMN new_column INT;

-- ✅ 正確做法:使用 Ghost 或類似工具

-- PostgreSQL 範例:使用 pg_repack
-- 1. 安裝 pg_repack extension
CREATE EXTENSION pg_repack;

-- 2. 執行線上重建
-- pg_repack -t large_table -d mydb

-- 手動實作 Ghost 策略 (適用於複雜情況)

-- Step 1: 建立新表 (含新欄位)
CREATE TABLE large_table_new (
  id BIGINT PRIMARY KEY,
  existing_column VARCHAR(255),
  new_column INT,  -- 新欄位
  created_at TIMESTAMP
);

-- Step 2: 建立觸發器同步變更
CREATE OR REPLACE FUNCTION sync_to_new_table()
RETURNS TRIGGER AS $$
BEGIN
  IF (TG_OP = 'INSERT') THEN
    INSERT INTO large_table_new VALUES (NEW.*);
  ELSIF (TG_OP = 'UPDATE') THEN
    UPDATE large_table_new SET
      existing_column = NEW.existing_column,
      new_column = NEW.new_column,
      created_at = NEW.created_at
    WHERE id = NEW.id;
  ELSIF (TG_OP = 'DELETE') THEN
    DELETE FROM large_table_new WHERE id = OLD.id;
  END IF;
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sync_trigger
AFTER INSERT OR UPDATE OR DELETE ON large_table
FOR EACH ROW EXECUTE FUNCTION sync_to_new_table();

-- Step 3: 背景批次複製既有資料
-- (使用腳本,分批執行避免鎖表)
DO $$
DECLARE
  batch_size INT := 10000;
  offset_val INT := 0;
  rows_affected INT;
BEGIN
  LOOP
    INSERT INTO large_table_new
    SELECT * FROM large_table
    ORDER BY id
    LIMIT batch_size OFFSET offset_val
    ON CONFLICT (id) DO NOTHING;

    GET DIAGNOSTICS rows_affected = ROW_COUNT;
    EXIT WHEN rows_affected = 0;

    offset_val := offset_val + batch_size;
    COMMIT; -- 每批次提交
    PERFORM pg_sleep(0.1); -- 避免過度負載
  END LOOP;
END $$;

-- Step 4: 驗證資料一致性
SELECT
  (SELECT COUNT(*) FROM large_table) as old_count,
  (SELECT COUNT(*) FROM large_table_new) as new_count;

-- Step 5: 切換表名 (需短暫鎖表)
BEGIN;
  DROP TRIGGER sync_trigger ON large_table;
  ALTER TABLE large_table RENAME TO large_table_old;
  ALTER TABLE large_table_new RENAME TO large_table;
COMMIT;

-- Step 6: 清理舊表 (確認無問題後)
DROP TABLE large_table_old;
```

### 5.3 資料庫版本控制

```javascript
// 使用 Knex.js Migrations

// migrations/20240124_add_user_preferences.js
exports.up = function(knex) {
  return knex.schema.createTable('user_preferences', (table) => {
    table.increments('id').primary();
    table.integer('user_id').unsigned().notNullable();
    table.jsonb('preferences').defaultTo('{}');
    table.timestamps(true, true);

    table.foreign('user_id').references('users.id').onDelete('CASCADE');
    table.index('user_id');
  });
};

exports.down = function(knex) {
  return knex.schema.dropTable('user_preferences');
};

// 執行遷移
// npx knex migrate:latest
// npx knex migrate:rollback

// 種子資料
// seeds/01_users.js
exports.seed = function(knex) {
  return knex('users').del()
    .then(function () {
      return knex('users').insert([
        { id: 1, name: 'John Doe', email: 'john@example.com' },
        { id: 2, name: 'Jane Smith', email: 'jane@example.com' }
      ]);
    });
};
```

---

## Part 6: 依賴關係解耦

### 6.1 識別緊耦合

```javascript
// 使用工具分析依賴關係
const madge = require('madge');

madge('src/')
  .then((res) => {
    // 找出循環依賴
    const circular = res.circular();
    if (circular.length > 0) {
      console.log('發現循環依賴:');
      circular.forEach(cycle => {
        console.log(cycle.join(' -> '));
      });
    }

    // 找出依賴最多的模組
    const dependencies = res.obj();
    const sorted = Object.entries(dependencies)
      .map(([file, deps]) => ({ file, count: deps.length }))
      .sort((a, b) => b.count - a.count);

    console.log('依賴最多的前 10 個模組:');
    sorted.slice(0, 10).forEach(({ file, count }) => {
      console.log(`${file}: ${count} dependencies`);
    });
  });
```

### 6.2 依賴注入模式

```typescript
// ❌ 緊耦合:直接依賴具體實作
class UserService {
  constructor() {
    this.db = new MySQLDatabase(); // 緊耦合!
    this.emailService = new SendGridEmailService(); // 緊耦合!
  }

  async createUser(userData) {
    const user = await this.db.insert('users', userData);
    await this.emailService.send(user.email, 'Welcome!');
    return user;
  }
}

// ✅ 鬆耦合:依賴注入
interface IDatabase {
  insert(table: string, data: any): Promise<any>;
  findOne(table: string, conditions: any): Promise<any>;
}

interface IEmailService {
  send(to: string, subject: string, body: string): Promise<void>;
}

class UserService {
  constructor(
    private db: IDatabase,
    private emailService: IEmailService
  ) {}

  async createUser(userData) {
    const user = await this.db.insert('users', userData);
    await this.emailService.send(user.email, 'Welcome!', '...');
    return user;
  }
}

// 使用 DI Container (例如 InversifyJS)
import { Container, injectable, inject } from 'inversify';

@injectable()
class MySQLDatabase implements IDatabase {
  async insert(table: string, data: any) { /* ... */ }
  async findOne(table: string, conditions: any) { /* ... */ }
}

@injectable()
class SendGridEmailService implements IEmailService {
  async send(to: string, subject: string, body: string) { /* ... */ }
}

@injectable()
class UserService {
  constructor(
    @inject('IDatabase') private db: IDatabase,
    @inject('IEmailService') private emailService: IEmailService
  ) {}

  // ...
}

// 配置 DI Container
const container = new Container();
container.bind<IDatabase>('IDatabase').to(MySQLDatabase);
container.bind<IEmailService>('IEmailService').to(SendGridEmailService);
container.bind<UserService>(UserService).toSelf();

// 使用
const userService = container.get<UserService>(UserService);
```

---

## Part 7: 漸進式架構現代化

### 7.1 從 Monolith 提取微服務

**識別服務邊界**:

```yaml
評估標準:

1. 業務能力 (Business Capability)
   - 是否代表獨立的業務功能?
   - 例如:訂單管理、庫存管理、用戶認證

2. 資料內聚性 (Data Cohesion)
   - 資料是否自包含?
   - 是否可以獨立資料庫?

3. 變更頻率 (Change Frequency)
   - 是否經常獨立變更?
   - 變更是否影響其他模組?

4. 團隊結構 (Team Structure)
   - 是否由獨立團隊負責?
   - Conway's Law

5. 擴展需求 (Scalability Needs)
   - 是否需要獨立擴展?
   - 資源需求是否不同?
```

**提取步驟**:

```javascript
// Step 1: 在 Monolith 內建立模組邊界
// src/modules/orders/OrderService.js
class OrderService {
  async createOrder(orderData) {
    // 只依賴 Order 相關資料
    const order = await OrderRepository.create(orderData);

    // 發布事件而非直接調用其他模組
    EventBus.publish('order.created', order);

    return order;
  }
}

// src/modules/inventory/InventoryService.js
class InventoryService {
  constructor() {
    // 監聽其他模組的事件
    EventBus.subscribe('order.created', this.handleOrderCreated.bind(this));
  }

  async handleOrderCreated(order) {
    // 更新庫存
    for (const item of order.items) {
      await this.decreaseStock(item.productId, item.quantity);
    }
  }
}

// Step 2: 提取為獨立服務
// order-service/src/index.js
const express = require('express');
const amqp = require('amqplib');

const app = express();

app.post('/orders', async (req, res) => {
  const order = await OrderService.createOrder(req.body);

  // 發布事件到 Message Queue
  const connection = await amqp.connect('amqp://localhost');
  const channel = await connection.createChannel();
  await channel.assertQueue('orders');
  channel.sendToQueue('orders', Buffer.from(JSON.stringify({
    event: 'order.created',
    data: order
  })));

  res.status(201).json(order);
});

app.listen(3001);

// inventory-service/src/index.js
const amqp = require('amqplib');

async function start() {
  const connection = await amqp.connect('amqp://localhost');
  const channel = await connection.createChannel();
  await channel.assertQueue('orders');

  channel.consume('orders', async (msg) => {
    const { event, data } = JSON.parse(msg.content.toString());

    if (event === 'order.created') {
      await InventoryService.handleOrderCreated(data);
      channel.ack(msg);
    }
  });
}

start();
```

---

## Part 7.5: 跨平台擴展與合規驅動變更 [v0.01 新增]

> 📌 **SOP 參考**: 完整流程見 [SOP.md](./SOP.md) 情境 F（跨平台）與情境 G（合規）

### 7.5.1 跨平台擴展策略

**平台識別觸發條件**：

```yaml
平台識別規則:
  觸發 Mobile Agent:
    - 變更涉及 Android/iOS 應用
    - 新增手機掃碼功能
    - 需要行動端 UI
    → 載入: sd-mobile-architect + qa-mobile-tester

  觸發 Integration Specialist:
    - 變更涉及硬體整合（條碼掃描器、IoT 設備）
    - 涉及第三方 API 整合
    → 載入: integration-specialist

  觸發 Compliance Officer:
    - 變更由法規/會計準則驅動
    - 涉及資安合規要求
    → 載入: compliance-officer
```

**跨平台 API 適配策略**：

```yaml
API 適配原則:
  1. 統一 API 層: 所有平台共用同一 Backend API
  2. 平台適配層: 為 Mobile/Desktop 提供 BFF (Backend for Frontend)
  3. 離線優先: Mobile 端考慮離線操作和資料同步
  4. 推播整合: Mobile 端整合推播通知機制
```

### 7.5.2 合規驅動變更策略

```yaml
合規變更特殊流程:
  1. 合規需求解讀: Compliance Officer 載入，解讀法規條文
  2. 業務影響分析: BA 驗證業務流程影響
  3. 實作方案: 確保變更符合法規要求
  4. 審計追蹤: 建立完整變更記錄
  5. 合規驗證: 驗證實作結果符合法規
  6. 文檔歸檔: 保留合規證明文件
```

---

## Part 8: 效能優化 - Legacy 系統特有問題

### 8.1 識別效能瓶頸

```javascript
// 使用 APM 工具
const newrelic = require('newrelic'); // 或 Elastic APM, Datadog

// 自訂效能追蹤
function measurePerformance(fn, name) {
  return async function(...args) {
    const start = Date.now();
    try {
      const result = await fn.apply(this, args);
      const duration = Date.now() - start;

      // 記錄慢操作
      if (duration > 1000) {
        console.warn(`Slow operation: ${name} took ${duration}ms`);
        newrelic.recordMetric(`Custom/SlowOperation/${name}`, duration);
      }

      return result;
    } catch (error) {
      newrelic.noticeError(error);
      throw error;
    }
  };
}

// 使用
const getUserOrders = measurePerformance(async (userId) => {
  const orders = await db.query('SELECT * FROM orders WHERE user_id = ?', [userId]);
  return orders;
}, 'getUserOrders');
```

### 8.2 資料庫查詢優化

```sql
-- 使用 EXPLAIN ANALYZE 分析慢查詢

-- ❌ 慢查詢
EXPLAIN ANALYZE
SELECT u.*, COUNT(o.id) as order_count
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE u.created_at > '2024-01-01'
GROUP BY u.id;

-- 結果顯示 Seq Scan (全表掃描)

-- ✅ 添加索引
CREATE INDEX idx_users_created_at ON users(created_at);
CREATE INDEX idx_orders_user_id ON orders(user_id);

-- 再次執行,應該使用 Index Scan

-- ✅ 進一步優化:物化視圖
CREATE MATERIALIZED VIEW user_order_counts AS
SELECT u.id, u.name, u.email, COUNT(o.id) as order_count
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
GROUP BY u.id, u.name, u.email;

-- 定期刷新
REFRESH MATERIALIZED VIEW user_order_counts;

-- 查詢時直接使用
SELECT * FROM user_order_counts WHERE order_count > 10;
```

---

## Part 9: 風險管理與回滾策略

### 9.1 Feature Toggles (功能開關)

```javascript
// 使用 unleash 或 LaunchDarkly

const unleash = require('unleash-client');

unleash.initialize({
  url: 'http://unleash.example.com/api/',
  appName: 'my-legacy-app',
  instanceId: 'instance-1'
});

// 在代碼中使用
app.post('/api/orders', async (req, res) => {
  // 使用新的訂單處理邏輯?
  if (unleash.isEnabled('new-order-processing')) {
    return newOrderService.create(req.body);
  } else {
    return legacyOrderService.create(req.body);
  }
});

// 漸進式推廣
unleash.isEnabled('new-feature', {
  userId: req.user.id,
  properties: {
    userType: req.user.type
  }
});

// Unleash 配置
// - Gradual Rollout: 0% -> 10% -> 50% -> 100%
// - Target specific users/segments
// - A/B testing
```

### 9.2 Canary Deployment (金絲雀部署)

```yaml
# Kubernetes Canary Deployment

# deployment-v1.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-v1
spec:
  replicas: 9  # 90% 流量
  selector:
    matchLabels:
      app: myapp
      version: v1
  template:
    metadata:
      labels:
        app: myapp
        version: v1
    spec:
      containers:
      - name: myapp
        image: myapp:v1

---
# deployment-v2.yaml (Canary)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-v2
spec:
  replicas: 1  # 10% 流量
  selector:
    matchLabels:
      app: myapp
      version: v2
  template:
    metadata:
      labels:
        app: myapp
        version: v2
    spec:
      containers:
      - name: myapp
        image: myapp:v2

---
# Service (共用)
apiVersion: v1
kind: Service
metadata:
  name: myapp
spec:
  selector:
    app: myapp  # 選擇所有 v1 和 v2
  ports:
  - port: 80
    targetPort: 8080
```

---

## Part 10: 真實案例研究

### Case Study: E-commerce 平台遺留系統現代化

**背景**:
- 10 年歷史的 PHP Monolith
- 500 萬行代碼
- 無測試覆蓋
- 技術債務嚴重
- 效能問題頻繁

**改造歷程**:

```yaml
Year 1: 穩定化
  - 添加 APM 監控
  - 建立 CI/CD Pipeline
  - 提升測試覆蓋至 30%
  - 修復關鍵安全漏洞

Year 2: 模組化
  - 在 Monolith 內建立模組邊界
  - 引入 Event Bus
  - 重構核心業務邏輯
  - 測試覆蓋提升至 60%

Year 3: 微服務化
  - 提取第一個微服務: Payment Service
  - 建立 API Gateway
  - 實施 Strangler Pattern
  - 資料庫分離

Year 4-5: 持續演進
  - 逐步提取更多微服務
  - 最終保留薄 Monolith (只有 UI 和路由)
  - 效能提升 10 倍
  - 部署頻率從每月 1 次提升至每天 10+ 次
```

**關鍵經驗**:

1. **不要大爆炸式重寫**
2. **先穩定化再現代化**
3. **測試是重構的安全網**
4. **漸進式提取服務**
5. **Feature Toggles 是最佳朋友**

---

## 總結

本深度技術指南涵蓋了 Brownfield 專案改造的進階主題:

✅ **代碼考古學** - 系統化理解 Legacy 系統的方法和工具
✅ **技術債務管理** - SQALE 方法、AISDLC TD_Score 公式、優先級矩陣
✅ **安全重構策略** - Strangler Fig、Branch by Abstraction、Parallel Change
✅ **功能停用策略** - 7 步漸進停用、停用檢查清單 [v0.01 新增]
✅ **測試策略** - Characterization Tests、Golden Master、漸進式覆蓋提升
✅ **資料庫遷移** - 零停機時間遷移、大型資料表處理、版本控制
✅ **依賴解耦** - 依賴注入、模組邊界、循環依賴消除
✅ **架構現代化** - 從 Monolith 到微服務的漸進式演進
✅ **跨平台與合規** - 平台識別、API 適配、合規驅動變更 [v0.01 新增]
✅ **效能優化** - Legacy 系統特有的效能瓶頸識別與解決
✅ **風險管理** - Feature Toggles、Canary Deployment、回滾策略
✅ **真實案例** - E-commerce 平台 5 年現代化之路

---

## 📚 延伸閱讀

- [Working Effectively with Legacy Code](https://www.amazon.com/Working-Effectively-Legacy-Michael-Feathers/dp/0131177052) - Michael Feathers
- [Refactoring](https://martinfowler.com/books/refactoring.html) - Martin Fowler
- [Strangler Fig Application](https://martinfowler.com/bliki/StranglerFigApplication.html)
- [Technical Debt Quadrant](https://martinfowler.com/bliki/TechnicalDebtQuadrant.html)
- [Branch by Abstraction](https://martinfowler.com/bliki/BranchByAbstraction.html)

---

**文檔版本: v0.01
**最後更新**: 2026-02-12
**維護者**: AISDLC Framework Team
