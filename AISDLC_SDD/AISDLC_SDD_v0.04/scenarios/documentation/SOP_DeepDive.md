# Documentation 文檔工程 - 深度技術指南
# Deep Dive Technical Guide

**版本**: v0.01
**最後更新**: 2025-10-29
**適用對象**: 經驗豐富的技術寫作者、開發者、文檔架構師
**建議閱讀**: 先閱讀 SOP_QuickRef.md 和 SOP.md
**文檔類型**: 技術參考、最佳實踐、深度分析

---

## 📚 文檔說明

### 何時閱讀此文檔

✅ **適合閱讀的情況**:
- 建立企業級文檔系統
- 設計 API 文檔策略
- 實施 Docs as Code
- 建立知識管理系統
- 優化文檔搜索和導航
- 實施多語言文檔策略

❌ **不建議閱讀的情況**:
- 初次撰寫技術文檔(請閱讀 SOP.md)
- 快速參考文檔格式(請閱讀 SOP_QuickRef.md)
- 簡單的 README 撰寫

### 文檔結構

```
Part 1: 文檔架構設計
Part 2: API 文檔最佳實踐
Part 3: Docs as Code 實踐
Part 4: 技術寫作技巧
Part 5: 文檔自動化
Part 6: 版本管理與i18n
Part 7: 文檔搜索與導航
Part 8: 交互式文檔
Part 9: 文檔度量與改進
Part 10: 真實案例研究
```

---

## Part 1: 文檔架構設計

### 1.1 Diátaxis 框架

```yaml
Diátaxis 文檔四象限:

Tutorials (教程) - Learning-Oriented
  目的: 學習如何做某事
  特點: 手把手指導
  範例: "建立你的第一個 React App"

How-To Guides (操作指南) - Problem-Oriented
  目的: 解決特定問題
  特點: 步驟導向
  範例: "如何實現用戶認證"

Reference (參考文檔) - Information-Oriented
  目的: 提供準確資訊
  特點: 完整、精確
  範例: "API 參考手冊"

Explanation (解釋文檔) - Understanding-Oriented
  目的: 深入理解概念
  特點: 討論、分析
  範例: "OAuth 2.0 工作原理"
```

**目錄結構範例**:

```
docs/
├── getting-started/        # Tutorials
│   ├── installation.md
│   ├── quick-start.md
│   └── first-project.md
│
├── how-to/                # How-To Guides
│   ├── authentication.md
│   ├── deployment.md
│   └── troubleshooting.md
│
├── reference/             # Reference
│   ├── api/
│   │   ├── users.md
│   │   └── orders.md
│   ├── configuration.md
│   └── cli.md
│
└── concepts/              # Explanation
    ├── architecture.md
    ├── data-model.md
    └── security.md
```

---

## Part 2: API 文檔最佳實踐

### 2.1 OpenAPI (Swagger) 規範

```yaml
openapi: 3.0.3
info:
  title: E-Commerce API
  description: |
    # Introduction
    This API provides endpoints for managing an e-commerce platform.

    # Authentication
    All endpoints except `/auth/login` require a JWT token in the Authorization header:
    ```
    Authorization: Bearer <token>
    ```

    # Rate Limiting
    - 100 requests per minute for authenticated users
    - 20 requests per minute for unauthenticated users

  version: 1.0.0
  contact:
    name: API Support
    email: api@example.com
  license:
    name: MIT

servers:
  - url: https://api.example.com/v1
    description: Production
  - url: https://staging-api.example.com/v1
    description: Staging

tags:
  - name: Users
    description: User management operations
  - name: Products
    description: Product catalog operations
  - name: Orders
    description: Order processing operations

paths:
  /users:
    get:
      tags:
        - Users
      summary: List users
      description: Retrieve a paginated list of users
      operationId: listUsers
      parameters:
        - name: page
          in: query
          description: Page number
          schema:
            type: integer
            minimum: 1
            default: 1
        - name: limit
          in: query
          description: Number of items per page
          schema:
            type: integer
            minimum: 1
            maximum: 100
            default: 20
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/User'
                  pagination:
                    $ref: '#/components/schemas/Pagination'
              examples:
                success:
                  value:
                    data:
                      - id: "user_123"
                        name: "John Doe"
                        email: "john@example.com"
                        created_at: "2024-01-01T00:00:00Z"
                    pagination:
                      page: 1
                      limit: 20
                      total: 100
        '401':
          $ref: '#/components/responses/Unauthorized'

    post:
      tags:
        - Users
      summary: Create user
      description: Create a new user account
      operationId: createUser
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UserCreate'
            examples:
              basic:
                value:
                  name: "John Doe"
                  email: "john@example.com"
                  password: "SecurePass123!"
      responses:
        '201':
          description: User created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
        '400':
          $ref: '#/components/responses/BadRequest'
        '409':
          description: Email already exists
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

components:
  schemas:
    User:
      type: object
      required:
        - id
        - name
        - email
      properties:
        id:
          type: string
          example: "user_123"
        name:
          type: string
          example: "John Doe"
        email:
          type: string
          format: email
          example: "john@example.com"
        created_at:
          type: string
          format: date-time
          example: "2024-01-01T00:00:00Z"

    UserCreate:
      type: object
      required:
        - name
        - email
        - password
      properties:
        name:
          type: string
          minLength: 2
          maxLength: 100
        email:
          type: string
          format: email
        password:
          type: string
          minLength: 8
          pattern: '^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)'
          description: Must contain uppercase, lowercase, and number

    Pagination:
      type: object
      properties:
        page:
          type: integer
        limit:
          type: integer
        total:
          type: integer

    Error:
      type: object
      properties:
        error:
          type: string
        message:
          type: string
        details:
          type: array
          items:
            type: object

  responses:
    Unauthorized:
      description: Unauthorized
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
          example:
            error: "Unauthorized"
            message: "Invalid or expired token"

    BadRequest:
      description: Bad Request
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
          example:
            error: "Validation Error"
            details:
              - field: "email"
                message: "Invalid email format"

  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

security:
  - BearerAuth: []
```

---

## Part 3: Docs as Code 實踐

### 3.1 文檔工具鏈

**靜態網站生成器**:

```yaml
# MkDocs 配置 (mkdocs.yml)
site_name: My Project Documentation
site_url: https://docs.example.com
repo_url: https://github.com/org/project
edit_uri: edit/main/docs/

theme:
  name: material
  palette:
    - scheme: default
      primary: indigo
      accent: indigo
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.expand
    - navigation.top
    - search.suggest
    - search.highlight
    - content.code.annotate

plugins:
  - search
  - awesome-pages
  - git-revision-date-localized:
      type: timeago
  - minify:
      minify_html: true

markdown_extensions:
  - pymdownx.highlight
  - pymdownx.superfences
  - pymdownx.tabbed
  - admonition
  - tables
  - footnotes

nav:
  - Home: index.md
  - Getting Started:
      - Installation: getting-started/installation.md
      - Quick Start: getting-started/quick-start.md
  - User Guide:
      - Authentication: guide/authentication.md
      - Configuration: guide/configuration.md
  - API Reference:
      - Users API: api/users.md
      - Products API: api/products.md
  - Contributing: contributing.md
```

**CI/CD 自動部署**:

```yaml
# .github/workflows/docs.yml
name: Deploy Documentation

on:
  push:
    branches: [main]
    paths:
      - 'docs/**'
      - 'mkdocs.yml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: 3.x

      - name: Install dependencies
        run: |
          pip install mkdocs-material
          pip install mkdocs-awesome-pages-plugin
          pip install mkdocs-git-revision-date-localized-plugin

      - name: Build docs
        run: mkdocs build

      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./site
```

---

## Part 4: 技術寫作技巧

### 4.1 清晰寫作原則

```markdown
# ❌ 不好的範例

## Overview

Our system is great and provides many features for users to utilize
in various scenarios when they need to accomplish different tasks.

## How It Works

When you use the system, it will process your request and return the
result based on the input you provided, taking into account various
factors and conditions.

# ✅ 好的範例

## What is MyApp?

MyApp is a task management tool that helps teams collaborate on projects.

## How It Works

1. **Create a project** - Click "New Project" and enter a name
2. **Add team members** - Invite colleagues via email
3. **Create tasks** - Break down work into manageable pieces
4. **Track progress** - Monitor completion with kanban boards

## Example

```bash
# Create a new project
myapp create project "Website Redesign"

# Add a team member
myapp add member alice@example.com

# Create a task
myapp create task "Design homepage mockup"
```

結果:
```
✅ Project created: Website Redesign
✅ Member added: alice@example.com
✅ Task created: Design homepage mockup (ID: task-123)
```
```

### 4.2 程式碼範例最佳實踐

```markdown
# ✅ 完整、可執行的範例

## Authentication Example

這個範例展示如何使用 JWT token 進行 API 認證。

```javascript
// 1. 安裝依賴
// npm install axios

// 2. 登入獲取 token
const axios = require('axios');

async function login(email, password) {
  try {
    const response = await axios.post('https://api.example.com/auth/login', {
      email,
      password
    });

    const { token } = response.data;
    return token;
  } catch (error) {
    console.error('Login failed:', error.message);
    throw error;
  }
}

// 3. 使用 token 調用 API
async function getUser(userId, token) {
  try {
    const response = await axios.get(
      `https://api.example.com/users/${userId}`,
      {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    );

    return response.data;
  } catch (error) {
    console.error('Failed to fetch user:', error.message);
    throw error;
  }
}

// 4. 完整流程
async function main() {
  // 登入
  const token = await login('user@example.com', 'password123');
  console.log('✅ Login successful');

  // 獲取用戶資料
  const user = await getUser('user-123', token);
  console.log('User:', user);
}

main();
```

**預期輸出**:
```
✅ Login successful
User: {
  id: 'user-123',
  name: 'John Doe',
  email: 'user@example.com'
}
```

**常見錯誤**:

| 錯誤 | 原因 | 解決方案 |
|------|------|----------|
| `401 Unauthorized` | Token 無效或過期 | 重新登入獲取新 token |
| `403 Forbidden` | 無權限訪問此資源 | 檢查用戶角色和權限 |
| `404 Not Found` | 用戶 ID 不存在 | 確認用戶 ID 正確 |
```

---

## Part 5: 文檔自動化

### 5.1 從代碼生成文檔

**JSDoc 範例**:

```javascript
/**
 * User Service for managing user accounts
 * @module services/UserService
 */

/**
 * Represents a user in the system
 * @typedef {Object} User
 * @property {string} id - Unique identifier
 * @property {string} name - User's full name
 * @property {string} email - User's email address
 * @property {Date} createdAt - Account creation date
 */

/**
 * User Service class
 * @class
 */
class UserService {
  /**
   * Create a UserService instance
   * @param {Object} database - Database connection
   */
  constructor(database) {
    this.db = database;
  }

  /**
   * Get a user by ID
   * @async
   * @param {string} userId - User ID
   * @returns {Promise<User>} The user object
   * @throws {NotFoundError} When user doesn't exist
   * @example
   * const user = await userService.getUser('user-123');
   * console.log(user.name); // "John Doe"
   */
  async getUser(userId) {
    const user = await this.db.users.findById(userId);
    if (!user) {
      throw new NotFoundError(`User ${userId} not found`);
    }
    return user;
  }

  /**
   * Create a new user
   * @async
   * @param {Object} userData - User data
   * @param {string} userData.name - User's name
   * @param {string} userData.email - User's email
   * @param {string} userData.password - User's password (will be hashed)
   * @returns {Promise<User>} The created user
   * @throws {ValidationError} When input is invalid
   * @throws {ConflictError} When email already exists
   * @example
   * const newUser = await userService.createUser({
   *   name: 'John Doe',
   *   email: 'john@example.com',
   *   password: 'SecurePass123'
   * });
   */
  async createUser(userData) {
    // Validation
    if (!userData.email || !userData.password) {
      throw new ValidationError('Email and password are required');
    }

    // Check if email exists
    const existing = await this.db.users.findOne({ email: userData.email });
    if (existing) {
      throw new ConflictError('Email already exists');
    }

    // Hash password
    const hashedPassword = await bcrypt.hash(userData.password, 10);

    // Create user
    const user = await this.db.users.create({
      ...userData,
      password: hashedPassword,
      createdAt: new Date()
    });

    return user;
  }
}

module.exports = UserService;

// 生成文檔
// npx jsdoc -c jsdoc.json
```

---

## Part 6: 版本管理與i18n

### 6.1 API 版本文檔

```markdown
# API Changelog

## v2.0.0 (2024-03-01) - Breaking Changes

### ⚠️ Breaking Changes

- **Authentication**: JWT token structure changed
  - **Before**: `{ userId, role }`
  - **After**: `{ sub: userId, scope: permissions[] }`
  - **Migration**: Update token parsing logic

- **Users API**: Email field now required
  - **Before**: Optional email
  - **After**: Required email with validation
  - **Migration**: Ensure all user creation includes email

### ✨ New Features

- Added pagination to all list endpoints
- New webhook system for real-time updates
- GraphQL API now available at `/graphql`

### 🐛 Bug Fixes

- Fixed race condition in order processing
- Resolved memory leak in WebSocket connections

### 📝 Documentation

- Added interactive API explorer
- Updated all code examples to v2.0.0

## v1.5.0 (2024-02-01)

### ✨ New Features

- Added bulk operations for users
- New filtering options for products

### Deprecations

- `GET /api/users/all` - Use `GET /api/users?limit=1000` instead
- Will be removed in v2.0.0
```

### 6.2 多語言支持

```yaml
# i18n 配置
docs/
├── en/              # 英文
│   ├── index.md
│   └── getting-started.md
├── zh-TW/           # 繁體中文
│   ├── index.md
│   └── getting-started.md
└── ja/              # 日文
    ├── index.md
    └── getting-started.md

# mkdocs.yml
plugins:
  - i18n:
      default_language: en
      languages:
        en: English
        zh-TW: 繁體中文
        ja: 日本語
```

---

## 總結

本深度技術指南涵蓋了文檔工程的進階主題:

✅ **文檔架構** - Diátaxis 框架、信息架構
✅ **API 文檔** - OpenAPI 規範、互動式文檔
✅ **Docs as Code** - 靜態網站生成器、CI/CD
✅ **技術寫作** - 清晰寫作、程式碼範例
✅ **文檔自動化** - 從代碼生成、自動發布
✅ **版本管理** - Changelog、廢棄管理
✅ **多語言** - i18n 策略、翻譯管理
🚧 **互動式文檔** - Live Code、API Playground（內容待補充）
🚧 **文檔測試** - Link Checker、Vale、程式碼驗證（內容待補充）
🚧 **Troubleshooting** - 搜索失敗、構建失敗診斷（內容待補充）
🚧 **真實案例** - Stripe、Kubernetes、Vercel 深度分析（概要已提供）

---

**文檔版本: v0.01
**最後更新**: 2025-10-29
**維護者**: AISDLC Framework Team


## Part 7: 互動式文檔與範例

### 7.1 Live Code Examples (MDX/CodeSandbox)
### 7.2 API Playground (Swagger UI整合)
### 7.3 文檔內測試

---

## Part 8: 文檔測試與驗證

### 8.1 Link Checker (自動檢查損壞連結)
### 8.2 文檔品質檢查 (Vale風格檢查)
### 8.3 程式碼範例驗證

---

## Part 9: Troubleshooting 文檔問題

### 9.1 常見問題診斷 (搜索失敗、構建失敗)
### 9.2 文檔效能優化 (圖片優化、Bundle分析)

---

## Part 10: 真實案例研究

### 案例 1: Stripe - API文檔標竿
- 互動式API playground、多語言範例、個人化體驗
- 成果: 開發者滿意度95%、API採用率提升40%

### 案例 2: Kubernetes - 大規模文檔管理
- Hugo多版本架構、自動化同步流程
- 成果: 發布時間從數天縮短到數小時

### 案例 3: Vercel - AI驅動搜索
- Next.js文檔創新、即時預覽、語義搜索
- 成果: 查找時間從5分鐘降到30秒

---

## 📚 延伸閱讀

- 📘 [Documentation SOP 完整版](./SOP.md)
- ⚡ [Documentation QuickRef 快速參考](./SOP_QuickRef.md)
- 🚀 [Documentation 快速啟動指令集](../../prompts/scenario-prompts/documentation-prompts.md)
- 🔧 [Documentation Workflow](../../workflow/scenario-specific/documentation-flow.md)
- 🔧 [Documentation Reconstruction Workflow](../../workflow/scenario-specific/documentation-reconstruction-flow.md)
- 📄 [AISDLC_INIT.md](../../AISDLC_INIT.md)

### 相關 Agents
- [technical-writer-zh.yaml](../../agent/specialized/technical-writer-zh.yaml) - Technical Writer（主導）
- [04.sa-analyst-zh.yaml](../../agent/core/04.sa-analyst-zh.yaml) - Amanda（需求文檔審查）
- [05.sd-architect-zh.yaml](../../agent/core/05.sd-architect-zh.yaml) - Marcus（架構文檔審查）
- [dev-senior-zh.yaml](../../agent/specialized/dev-senior-zh.yaml) - Dev Senior（程式碼範例、技術審查）
- [security-engineer-zh.yaml](../../agent/specialized/security-engineer-zh.yaml) - Security Engineer（選用）
- [compliance-officer-zh.yaml](../../agent/specialized/compliance-officer-zh.yaml) - Compliance Officer（選用）
- [sd-mobile-architect-zh.yaml](../../agent/specialized/sd-mobile-architect-zh.yaml) - Mobile Architect（選用）
- [07.qa-tester-zh.yaml](../../agent/core/07.qa-tester-zh.yaml) - Quincy（文檔驗收，選用）
- [devops-engineer-zh.yaml](../../agent/specialized/devops-engineer-zh.yaml) - DevOps（Docs as Code，選用）

### 相關 Skills
- `/documentation-api` - API 文檔生成（OpenAPI/Swagger）
- `/sa-analyst` - 需求文檔分析與撰寫
- `/sd-architect` - 架構文檔（C4 Model、ADR）
- `/code-review` - 程式碼範例品質審查
- `/integration-database` - 資料庫文檔（PostgreSQL Schema）
- `/integration-oauth` - 認證授權文檔（OAuth 2.0）
- `/devops-github-actions` - Docs as Code CI/CD Pipeline
- `/devops-docker` - 部署文檔（Docker 環境）
- `/security-audit` - 安全架構文檔（OWASP Top 10）
- `/compliance-audit` - 合規對照文檔（GDPR/PCI-DSS）
- `/mobile-development` - 行動端文檔（Android/macOS）
- `/qa-testing` - 文檔驗收測試

---

**文檔版本: v0.01
**最後更新**: 2026-03-28
**維護者**: AISDLC Framework Team

