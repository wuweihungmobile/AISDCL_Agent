---
name: documentation-api
description: 生成 API 文檔，支援 OpenAPI/Swagger 規格，包含端點說明和範例
user-invocable: true
disable-model-invocation: false
argument-hint: "[format: 文檔格式 (openapi/markdown/both)] [source: API 來源 (code/existing-spec)]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# Documentation API Skill

基於 AISDLC Documentation 情境的 API 文檔生成技能。

---

## 觸發方式

```bash
/doc-api                       # 生成 API 文檔
/doc-api openapi               # 生成 OpenAPI 規格
/doc-api markdown              # 生成 Markdown 文檔
/doc-api --format=both         # 兩種格式都生成
```

---

## 執行流程

### 階段 1: API 端點掃描 (10分鐘)

**掃描項目**:
- [ ] 所有 API 路由
- [ ] HTTP 方法
- [ ] 請求/回應格式
- [ ] 認證需求
- [ ] 錯誤碼定義

**自動掃描命令**:
```bash
# 尋找路由定義
grep -r "app\.\(get\|post\|put\|delete\|patch\)" src/
grep -r "router\.\(get\|post\|put\|delete\|patch\)" src/

# Next.js App Router
find app/api -name "route.ts"
```

---

### 階段 2: OpenAPI 規格生成

```yaml
# openapi.yaml
openapi: 3.0.3
info:
  title: {{project_name}} API
  description: {{description}}
  version: 1.0.0
  contact:
    email: api@example.com

servers:
  - url: https://api.example.com/v1
    description: Production
  - url: https://staging-api.example.com/v1
    description: Staging

tags:
  - name: Users
    description: 用戶管理相關 API
  - name: Products
    description: 產品相關 API

paths:
  /users:
    get:
      tags: [Users]
      summary: 取得用戶列表
      description: 取得所有用戶的分頁列表
      operationId: getUsers
      parameters:
        - name: page
          in: query
          schema:
            type: integer
            default: 1
        - name: limit
          in: query
          schema:
            type: integer
            default: 20
      responses:
        '200':
          description: 成功取得用戶列表
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserListResponse'
        '401':
          $ref: '#/components/responses/Unauthorized'
      security:
        - bearerAuth: []

    post:
      tags: [Users]
      summary: 建立新用戶
      operationId: createUser
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateUserRequest'
      responses:
        '201':
          description: 用戶建立成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
        '400':
          $ref: '#/components/responses/BadRequest'

components:
  schemas:
    User:
      type: object
      properties:
        id:
          type: string
          format: uuid
        email:
          type: string
          format: email
        name:
          type: string
        createdAt:
          type: string
          format: date-time
      required: [id, email, name]

    CreateUserRequest:
      type: object
      properties:
        email:
          type: string
          format: email
        name:
          type: string
        password:
          type: string
          minLength: 8
      required: [email, name, password]

    UserListResponse:
      type: object
      properties:
        data:
          type: array
          items:
            $ref: '#/components/schemas/User'
        pagination:
          $ref: '#/components/schemas/Pagination'

    Pagination:
      type: object
      properties:
        page:
          type: integer
        limit:
          type: integer
        total:
          type: integer
        totalPages:
          type: integer

    Error:
      type: object
      properties:
        code:
          type: string
        message:
          type: string

  responses:
    Unauthorized:
      description: 未授權
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    BadRequest:
      description: 請求格式錯誤
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'

  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
```

---

### 階段 3: Markdown 文檔生成

```markdown
# API 文檔

## 概覽

- **Base URL**: `https://api.example.com/v1`
- **認證方式**: Bearer Token (JWT)
- **回應格式**: JSON

## 認證

所有需要認證的 API 需在 Header 加入:

```
Authorization: Bearer <token>
```

---

## 用戶 API

### GET /users

取得用戶列表

**參數**:
| 名稱 | 位置 | 類型 | 必要 | 說明 |
|------|------|------|------|------|
| page | query | integer | 否 | 頁碼，預設 1 |
| limit | query | integer | 否 | 每頁數量，預設 20 |

**回應範例**:
```json
{
  "data": [
    {
      "id": "uuid",
      "email": "user@example.com",
      "name": "John Doe",
      "createdAt": "2024-01-01T00:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "totalPages": 5
  }
}
```

### POST /users

建立新用戶

**請求 Body**:
```json
{
  "email": "user@example.com",
  "name": "John Doe",
  "password": "securePassword123"
}
```

**回應**: 201 Created
```

---

### 階段 4: 文檔驗證

**驗證工具**:
```bash
# OpenAPI 驗證
npx @redocly/cli lint openapi.yaml

# 生成 HTML 文檔
npx @redocly/cli build-docs openapi.yaml -o docs/api.html
```

**驗證清單**:
- [ ] 所有端點已記錄
- [ ] 請求/回應範例完整
- [ ] 錯誤碼說明清楚
- [ ] 認證方式說明正確

---

## 產出物

| 產出物 | 路徑 | 說明 |
|--------|------|------|
| OpenAPI 規格 | `openapi.yaml` | 標準 API 規格 |
| API 文檔 | `docs/api/README.md` | Markdown 版文檔 |
| HTML 文檔 | `docs/api.html` | 可瀏覽的 HTML |

---

## 相關 Skill

- `/sa-analyze` - 需求分析
- `/testing` - API 測試

---


## 相關檔案

- SOP 參考: `scenarios/documentation/SOP_QuickRef.md`

**基於**: AISDLC v0.09 Documentation 情境
