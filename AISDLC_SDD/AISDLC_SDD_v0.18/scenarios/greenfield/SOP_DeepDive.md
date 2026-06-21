# Greenfield Project 新專案開發 - 深度技術指南
# Deep Dive Technical Guide

**版本**: v0.01
**最後更新**: 2026-02-15
**適用對象**: 經驗豐富的技術主管、架構師、資深開發者
**建議閱讀**: 先閱讀 SOP_QuickRef.md 和 SOP.md
**文檔類型**: 技術參考、最佳實踐、深度分析

---

## 📚 文檔說明

### 何時閱讀此文檔

✅ **適合閱讀的情況**:
- 需要設計複雜的微服務架構
- 選擇技術棧時面臨多個選項
- 處理高併發、高可用性需求
- 實施 CI/CD 和 DevOps 流程
- 設計可擴展的資料庫架構
- Troubleshooting 架構問題

❌ **不建議閱讀的情況**:
- 初次執行 Greenfield 專案（請閱讀 SOP.md）
- 快速參考流程（請閱讀 SOP_QuickRef.md）
- 簡單的 CRUD 應用開發

### 文檔結構

```
Part 1: 技術選型深度分析
Part 2: 架構設計模式
Part 3: 資料庫設計進階
Part 4: API 設計最佳實踐
Part 5: 前端架構策略
Part 6: CI/CD 與 DevOps
Part 7: 效能與擴展性
Part 8: 安全性設計
Part 9: Troubleshooting Guide
Part 10: 真實案例研究
```

---

## Part 1: 技術選型深度分析

### 1.1 前端框架選擇矩陣

#### React vs Vue vs Angular - 決策樹

**使用 React 的場景**:

```yaml
適合情況:
  ✅ 需要靈活的架構（自由選擇狀態管理、路由）
  ✅ 團隊熟悉 JavaScript ES6+ 和 JSX
  ✅ 需要豐富的第三方生態系統
  ✅ 大型應用需要精細的效能優化
  ✅ 需要 React Native 做跨平台開發

技術特性:
  - 虛擬 DOM 和 Reconciliation 算法
  - 單向數據流
  - Hooks API (useState, useEffect, useContext)
  - 靈活但需要更多決策

生態系統:
  - 狀態管理: Redux, MobX, Zustand, Recoil
  - 路由: React Router, Next.js (SSR)
  - UI 庫: Material-UI, Ant Design, Chakra UI
  - 測試: Jest, React Testing Library

最佳實踐範例:
```javascript
// 現代 React 架構 (2024)
// 使用 Hooks + Context + Custom Hooks

// 1. 資料獲取 Hook
import { useState, useEffect } from 'react';

function useAPI(endpoint) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const controller = new AbortController();

    async function fetchData() {
      try {
        const response = await fetch(`/api/${endpoint}`, {
          signal: controller.signal
        });
        const json = await response.json();
        setData(json);
      } catch (err) {
        if (err.name !== 'AbortError') {
          setError(err);
        }
      } finally {
        setLoading(false);
      }
    }

    fetchData();

    return () => controller.abort(); // Cleanup
  }, [endpoint]);

  return { data, loading, error };
}

// 2. 使用 Custom Hook
function UserProfile({ userId }) {
  const { data: user, loading, error } = useAPI(`users/${userId}`);

  if (loading) return <Skeleton />;
  if (error) return <ErrorMessage error={error} />;

  return (
    <div>
      <h1>{user.name}</h1>
      <p>{user.email}</p>
    </div>
  );
}

// 3. 全域狀態管理 (使用 Zustand)
import create from 'zustand';

const useStore = create((set) => ({
  user: null,
  login: (userData) => set({ user: userData }),
  logout: () => set({ user: null }),
}));

function App() {
  const { user, login, logout } = useStore();

  return (
    <div>
      {user ? (
        <UserDashboard user={user} onLogout={logout} />
      ) : (
        <LoginForm onLogin={login} />
      )}
    </div>
  );
}
```
```

**使用 Vue 的場景**:

```yaml
適合情況:
  ✅ 團隊偏好漸進式框架（易於學習）
  ✅ 需要快速開發和原型驗證
  ✅ 中小型應用且不需要過度工程化
  ✅ 偏好模板語法而非 JSX
  ✅ 需要官方完整解決方案（Vuex, Vue Router, Vue CLI）

技術特性:
  - 響應式數據綁定（Vue 3 Composition API）
  - 單文件組件 (SFC)
  - 模板語法（更接近 HTML）
  - 官方生態系統整合度高

生態系統:
  - 狀態管理: Pinia (Vuex 5)
  - 路由: Vue Router
  - UI 庫: Vuetify, Element Plus, Quasar
  - SSR: Nuxt.js
  - 測試: Vitest, Vue Test Utils

最佳實踐範例:
```vue
<!-- Vue 3 Composition API 範例 -->
<template>
  <div class="user-profile">
    <LoadingSpinner v-if="loading" />
    <ErrorMessage v-else-if="error" :error="error" />
    <div v-else>
      <h1>{{ user.name }}</h1>
      <p>{{ user.email }}</p>
      <button @click="updateUser">Update</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useUserStore } from '@/stores/user';

const props = defineProps({
  userId: String
});

const userStore = useUserStore();
const user = ref(null);
const loading = ref(true);
const error = ref(null);

async function fetchUser() {
  try {
    loading.value = true;
    const response = await fetch(`/api/users/${props.userId}`);
    user.value = await response.json();
  } catch (err) {
    error.value = err;
  } finally {
    loading.value = false;
  }
}

async function updateUser() {
  await userStore.updateUser(user.value);
}

onMounted(() => {
  fetchUser();
});
</script>

<style scoped>
.user-profile {
  padding: 20px;
}
</style>
```

<!-- Pinia Store 範例 -->
```javascript
// stores/user.js
import { defineStore } from 'pinia';

export const useUserStore = defineStore('user', {
  state: () => ({
    currentUser: null,
    isAuthenticated: false
  }),

  getters: {
    userName: (state) => state.currentUser?.name || 'Guest'
  },

  actions: {
    async login(credentials) {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify(credentials)
      });
      const user = await response.json();
      this.currentUser = user;
      this.isAuthenticated = true;
    },

    logout() {
      this.currentUser = null;
      this.isAuthenticated = false;
    }
  }
});
```
```

**使用 Angular 的場景**:

```yaml
適合情況:
  ✅ 企業級大型應用（強型別、完整架構）
  ✅ 團隊熟悉 TypeScript 和 OOP
  ✅ 需要完整的官方解決方案（開箱即用）
  ✅ 長期維護的複雜應用
  ✅ 需要嚴格的程式碼規範

技術特性:
  - TypeScript 強型別
  - 依賴注入 (Dependency Injection)
  - RxJS 響應式編程
  - CLI 和工具鏈完整
  - 模組化架構

生態系統:
  - 狀態管理: NgRx (Redux pattern)
  - UI 庫: Angular Material, PrimeNG
  - 測試: Jasmine, Karma, Protractor
  - SSR: Angular Universal

最佳實踐範例:
```typescript
// user.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, catchError, tap } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class UserService {
  private apiUrl = '/api/users';

  constructor(private http: HttpClient) {}

  getUser(id: string): Observable<User> {
    return this.http.get<User>(`${this.apiUrl}/${id}`).pipe(
      tap(user => console.log('Fetched user:', user)),
      catchError(this.handleError)
    );
  }

  private handleError(error: any): Observable<never> {
    console.error('API Error:', error);
    throw error;
  }
}

// user-profile.component.ts
import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { UserService } from './user.service';

@Component({
  selector: 'app-user-profile',
  templateUrl: './user-profile.component.html',
  styleUrls: ['./user-profile.component.css']
})
export class UserProfileComponent implements OnInit {
  user$ = this.userService.getUser(this.route.snapshot.params['id']);

  constructor(
    private userService: UserService,
    private route: ActivatedRoute
  ) {}

  ngOnInit(): void {}
}
```

```html
<!-- user-profile.component.html -->
<div class="user-profile">
  <ng-container *ngIf="user$ | async as user; else loading">
    <h1>{{ user.name }}</h1>
    <p>{{ user.email }}</p>
  </ng-container>

  <ng-template #loading>
    <app-loading-spinner></app-loading-spinner>
  </ng-template>
</div>
```
```

#### 決策矩陣總結

| 考量因素 | React | Vue | Angular |
|---------|-------|-----|---------|
| **學習曲線** | 中 | 易 | 難 |
| **靈活性** | 高 | 中 | 低 |
| **生態系統** | 最豐富 | 豐富 | 官方完整 |
| **TypeScript 支援** | 良好 | 良好 | 原生 |
| **大型應用** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **快速開發** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| **效能** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **企業採用** | 高 | 中 | 高 |

### 1.2 後端技術選型

#### Node.js vs Python vs Go vs Java

**Node.js (Express/Fastify/NestJS)**:

```yaml
適合場景:
  ✅ JavaScript 全端開發（共用程式碼）
  ✅ I/O 密集型應用（API、即時通訊）
  ✅ 微服務架構
  ✅ 快速原型開發

範例架構:
```javascript
// NestJS 企業級架構範例

// user.controller.ts
import { Controller, Get, Post, Body, Param, UseGuards } from '@nestjs/common';
import { UserService } from './user.service';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';

@Controller('users')
export class UserController {
  constructor(private readonly userService: UserService) {}

  @UseGuards(JwtAuthGuard)
  @Get(':id')
  async findOne(@Param('id') id: string) {
    return this.userService.findOne(id);
  }

  @Post()
  async create(@Body() createUserDto: CreateUserDto) {
    return this.userService.create(createUserDto);
  }
}

// user.service.ts
import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { User } from './user.entity';

@Injectable()
export class UserService {
  constructor(
    @InjectRepository(User)
    private userRepository: Repository<User>,
  ) {}

  async findOne(id: string): Promise<User> {
    const user = await this.userRepository.findOne({ where: { id } });
    if (!user) {
      throw new NotFoundException(`User with ID ${id} not found`);
    }
    return user;
  }

  async create(createUserDto: CreateUserDto): Promise<User> {
    const user = this.userRepository.create(createUserDto);
    return this.userRepository.save(user);
  }
}
```

優勢:
  - 非阻塞 I/O（高併發處理）
  - NPM 生態系統龐大
  - 前後端語言統一
  - 微服務友好

劣勢:
  - CPU 密集型任務表現差
  - 單執行緒（需使用 Cluster）
  - Callback hell（雖然 async/await 改善了）
```

**Python (Django/FastAPI)**:

```yaml
適合場景:
  ✅ 資料科學、機器學習整合
  ✅ 快速開發（Django Admin、ORM）
  ✅ API 服務（FastAPI 效能優異）
  ✅ 自動化腳本、資料處理

範例架構:
```python
# FastAPI 現代 API 架構

from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

app = FastAPI()

# Models
class UserCreate(BaseModel):
    name: str
    email: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        orm_mode = True

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Routes
@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/users", response_model=UserResponse, status_code=201)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# 自動生成 OpenAPI 文檔
# 訪問 /docs 查看 Swagger UI
```

優勢:
  - 開發速度快（語法簡潔）
  - AI/ML 生態系統完整（TensorFlow, PyTorch）
  - Django ORM 強大
  - FastAPI 效能接近 Go

劣勢:
  - 執行效能較低（與 Go/Java 相比）
  - GIL 限制多執行緒效能
  - 部署相對複雜（虛擬環境管理）
```

**Go (Gin/Echo)**:

```yaml
適合場景:
  ✅ 高效能、高併發服務
  ✅ 微服務架構
  ✅ 系統工具、CLI 開發
  ✅ 雲原生應用（Kubernetes, Docker）

範例架構:
```go
// Gin 框架範例

package main

import (
    "github.com/gin-gonic/gin"
    "gorm.io/gorm"
    "net/http"
)

type User struct {
    ID    uint   `json:"id" gorm:"primaryKey"`
    Name  string `json:"name" binding:"required"`
    Email string `json:"email" binding:"required,email"`
}

type UserHandler struct {
    db *gorm.DB
}

func (h *UserHandler) GetUser(c *gin.Context) {
    id := c.Param("id")
    var user User

    if err := h.db.First(&user, id).Error; err != nil {
        c.JSON(http.StatusNotFound, gin.H{"error": "User not found"})
        return
    }

    c.JSON(http.StatusOK, user)
}

func (h *UserHandler) CreateUser(c *gin.Context) {
    var user User

    if err := c.ShouldBindJSON(&user); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }

    if err := h.db.Create(&user).Error; err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to create user"})
        return
    }

    c.JSON(http.StatusCreated, user)
}

func main() {
    r := gin.Default()

    // Middleware
    r.Use(gin.Logger())
    r.Use(gin.Recovery())

    // Routes
    userHandler := &UserHandler{db: initDB()}
    r.GET("/users/:id", userHandler.GetUser)
    r.POST("/users", userHandler.CreateUser)

    r.Run(":8080")
}
```

優勢:
  - 編譯型語言（效能接近 C++）
  - 原生並發支援（Goroutines）
  - 部署簡單（單一執行檔）
  - 記憶體佔用低

劣勢:
  - 學習曲線較陡（語法獨特）
  - 生態系統相對年輕
  - 泛型支援較晚（Go 1.18+）
  - 錯誤處理冗長
```

#### 後端技術選型決策樹

```
開始
  │
  ├─ 需要AI/ML整合? ─ 是 → Python (FastAPI)
  │       │
  │       否
  │       │
  ├─ 需要極致效能/高併發? ─ 是 → Go
  │       │
  │       否
  │       │
  ├─ 團隊是 JavaScript? ─ 是 → Node.js (NestJS)
  │       │
  │       否
  │       │
  ├─ 企業級應用/複雜業務邏輯? ─ 是 → Java (Spring Boot)
  │       │
  │       否
  │       │
  └─ 快速原型/快速開發? → Python (Django) 或 Node.js
```

---

## Part 2: 架構設計模式

### 2.1 單體 vs 微服務 vs Serverless

#### 決策框架

**單體架構 (Monolith)**:

```yaml
適合場景:
  ✅ 團隊規模 < 10 人
  ✅ MVP 快速驗證
  ✅ 業務邏輯緊密耦合
  ✅ 部署和維護成本優先

架構範例:
```
┌─────────────────────────────────────┐
│         Monolithic Application       │
├─────────────────────────────────────┤
│  ┌─────────┐  ┌──────────┐          │
│  │  Web UI │  │  API     │          │
│  └─────────┘  └──────────┘          │
│  ┌───────────────────────┐          │
│  │   Business Logic      │          │
│  └───────────────────────┘          │
│  ┌───────────────────────┐          │
│  │   Data Access Layer   │          │
│  └───────────────────────┘          │
└─────────────────────────────────────┘
              │
         ┌────┴────┐
         │ Database │
         └─────────┘
```

優勢:
  - 開發簡單直接
  - 部署簡單（單一應用）
  - 測試容易（端到端）
  - 效能好（無網路呼叫）

劣勢:
  - 擴展困難（需整體擴展）
  - 技術棧鎖定
  - 部署風險高（全部或無）
  - 程式碼庫龐大後難以維護
```

**微服務架構 (Microservices)**:

```yaml
適合場景:
  ✅ 團隊規模 > 20 人（多團隊協作）
  ✅ 需要獨立擴展不同服務
  ✅ 不同服務有不同技術需求
  ✅ 持續部署和演進

架構範例:
```
                    ┌──────────────┐
                    │  API Gateway │
                    └──────┬───────┘
            ┌──────────────┼──────────────┐
            │              │              │
      ┌─────▼────┐   ┌─────▼────┐  ┌─────▼────┐
      │  User    │   │  Order   │  │ Payment  │
      │  Service │   │  Service │  │ Service  │
      └─────┬────┘   └─────┬────┘  └─────┬────┘
            │              │              │
      ┌─────▼────┐   ┌─────▼────┐  ┌─────▼────┐
      │  User DB │   │ Order DB │  │Payment DB│
      └──────────┘   └──────────┘  └──────────┘

通訊方式:
  - 同步: REST API, gRPC
  - 非同步: Message Queue (RabbitMQ, Kafka)
  - 服務發現: Consul, Eureka
```

範例實作:
```javascript
// User Service (Node.js + Express)
const express = require('express');
const app = express();

app.get('/api/users/:id', async (req, res) => {
  const user = await db.users.findOne(req.params.id);
  res.json(user);
});

app.listen(3001);

// Order Service (Python + FastAPI)
from fastapi import FastAPI
import httpx

app = FastAPI()

@app.post("/api/orders")
async def create_order(order: Order):
    # 呼叫 User Service 驗證使用者
    async with httpx.AsyncClient() as client:
        user = await client.get(f"http://user-service:3001/api/users/{order.user_id}")

    # 呼叫 Payment Service 處理付款
    async with httpx.AsyncClient() as client:
        payment = await client.post("http://payment-service:3002/api/payments", json=order.dict())

    # 建立訂單
    db_order = await create_order_in_db(order)
    return db_order
```

優勢:
  - 獨立部署和擴展
  - 技術多樣性
  - 容錯性高（單一服務故障不影響全局）
  - 團隊自主性

劣勢:
  - 複雜度高（分散式系統）
  - 運維成本高（監控、日誌、追蹤）
  - 資料一致性挑戰
  - 網路延遲和失敗處理
```

**Serverless 架構**:

```yaml
適合場景:
  ✅ 事件驅動應用
  ✅ 不規則流量（間歇性高峰）
  ✅ 快速擴展需求
  ✅ 降低運維成本

架構範例 (AWS Lambda):
```javascript
// Lambda Function: User CRUD
exports.handler = async (event) => {
  const { httpMethod, pathParameters, body } = event;

  switch (httpMethod) {
    case 'GET':
      // 從 DynamoDB 讀取
      const user = await dynamodb.get({
        TableName: 'Users',
        Key: { id: pathParameters.id }
      }).promise();
      return {
        statusCode: 200,
        body: JSON.stringify(user.Item)
      };

    case 'POST':
      // 寫入 DynamoDB
      const userData = JSON.parse(body);
      await dynamodb.put({
        TableName: 'Users',
        Item: userData
      }).promise();
      return {
        statusCode: 201,
        body: JSON.stringify(userData)
      };

    default:
      return { statusCode: 405, body: 'Method Not Allowed' };
  }
};

// API Gateway 配置 (serverless.yml)
functions:
  getUser:
    handler: users.handler
    events:
      - http:
          path: users/{id}
          method: get
      - http:
          path: users
          method: post
```

優勢:
  - 無伺服器管理（自動擴展）
  - 按需計費（節省成本）
  - 快速部署
  - 內建高可用性

劣勢:
  - Cold start 延遲
  - 供應商鎖定
  - 除錯困難
  - 長時間執行任務不適合（通常有 timeout 限制）
```

### 2.2 資料庫架構模式

#### 關聯式 vs NoSQL vs NewSQL

**PostgreSQL (關聯式資料庫)**:

```sql
-- 進階 PostgreSQL 功能範例

-- 1. JSONB 支援（混合模式）
CREATE TABLE products (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  price DECIMAL(10, 2),
  attributes JSONB, -- 彈性屬性（顏色、尺寸等）
  created_at TIMESTAMP DEFAULT NOW()
);

-- 查詢 JSONB
SELECT * FROM products
WHERE attributes @> '{"color": "red"}'; -- 包含查詢
WHERE attributes->>'size' = 'L'; -- 提取查詢

-- 2. 全文搜索
CREATE INDEX products_name_idx ON products USING gin(to_tsvector('english', name));

SELECT * FROM products
WHERE to_tsvector('english', name) @@ to_tsquery('laptop & gaming');

-- 3. 分區表 (Partitioning) - 處理大量資料
CREATE TABLE orders (
  id BIGSERIAL,
  user_id INT,
  order_date DATE NOT NULL,
  total DECIMAL(10, 2)
) PARTITION BY RANGE (order_date);

CREATE TABLE orders_2024_q1 PARTITION OF orders
  FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');

CREATE TABLE orders_2024_q2 PARTITION OF orders
  FOR VALUES FROM ('2024-04-01') TO ('2024-07-01');

-- 4. 資料庫觸發器 (Triggers) - 自動化邏輯
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

**MongoDB (文件導向 NoSQL)**:

```javascript
// MongoDB 進階模式

// 1. 嵌入 vs 引用 (Embedding vs Referencing)

// 嵌入式（適合一對少量）
{
  _id: ObjectId("..."),
  name: "John Doe",
  email: "john@example.com",
  addresses: [
    { street: "123 Main St", city: "NYC", type: "home" },
    { street: "456 Work Ave", city: "NYC", type: "office" }
  ]
}

// 引用式（適合一對多、多對多）
// Users Collection
{
  _id: ObjectId("user1"),
  name: "John Doe",
  email: "john@example.com"
}

// Orders Collection
{
  _id: ObjectId("order1"),
  user_id: ObjectId("user1"), // 引用
  items: [...],
  total: 100
}

// 2. 聚合管道 (Aggregation Pipeline)
db.orders.aggregate([
  // Stage 1: Match（過濾）
  { $match: { status: "completed", order_date: { $gte: new Date("2024-01-01") } } },

  // Stage 2: Lookup（JOIN）
  { $lookup: {
      from: "users",
      localField: "user_id",
      foreignField: "_id",
      as: "user"
  }},

  // Stage 3: Unwind（展開陣列）
  { $unwind: "$user" },

  // Stage 4: Group（分組聚合）
  { $group: {
      _id: "$user.email",
      totalOrders: { $sum: 1 },
      totalRevenue: { $sum: "$total" }
  }},

  // Stage 5: Sort（排序）
  { $sort: { totalRevenue: -1 } },

  // Stage 6: Limit
  { $limit: 10 }
]);

// 3. 變更流 (Change Streams) - 即時監聽資料變化
const changeStream = db.orders.watch();

changeStream.on('change', (change) => {
  if (change.operationType === 'insert') {
    console.log('New order:', change.fullDocument);
    // 觸發通知、更新快取等
  }
});

// 4. 索引策略
db.users.createIndex({ email: 1 }, { unique: true });
db.orders.createIndex({ user_id: 1, order_date: -1 }); // 複合索引
db.products.createIndex({ name: "text" }); // 全文索引
```

**Redis (快取 + 資料結構)**:

```javascript
// Redis 進階使用模式

const Redis = require('ioredis');
const redis = new Redis();

// 1. 快取模式（Cache-Aside Pattern）
async function getUser(userId) {
  // 先查快取
  const cached = await redis.get(`user:${userId}`);
  if (cached) {
    return JSON.parse(cached);
  }

  // 快取未命中，查資料庫
  const user = await db.users.findOne(userId);

  // 寫入快取（設定過期時間）
  await redis.setex(`user:${userId}`, 3600, JSON.stringify(user));

  return user;
}

// 2. 分散式鎖 (Distributed Lock)
async function acquireLock(resource, timeout = 10000) {
  const lockKey = `lock:${resource}`;
  const lockValue = Date.now() + timeout;

  const acquired = await redis.set(lockKey, lockValue, 'PX', timeout, 'NX');
  return acquired === 'OK';
}

async function releaseLock(resource) {
  await redis.del(`lock:${resource}`);
}

// 使用範例（防止重複處理）
async function processPayment(orderId) {
  const locked = await acquireLock(`payment:${orderId}`);
  if (!locked) {
    throw new Error('Payment already processing');
  }

  try {
    // 處理付款邏輯
    await chargeCustomer(orderId);
  } finally {
    await releaseLock(`payment:${orderId}`);
  }
}

// 3. Pub/Sub（即時通訊）
// Publisher
await redis.publish('notifications', JSON.stringify({
  type: 'order_completed',
  userId: 'user123',
  orderId: 'order456'
}));

// Subscriber
const subscriber = new Redis();
subscriber.subscribe('notifications');
subscriber.on('message', (channel, message) => {
  const data = JSON.parse(message);
  console.log('Notification:', data);
  // 推送給使用者（WebSocket, SSE）
});

// 4. 排行榜（Sorted Sets）
// 新增分數
await redis.zadd('leaderboard', 1500, 'player1');
await redis.zadd('leaderboard', 2000, 'player2');

// 取得排行（降序）
const topPlayers = await redis.zrevrange('leaderboard', 0, 9, 'WITHSCORES');
// ['player2', '2000', 'player1', '1500', ...]

// 5. 限流（Rate Limiting）
async function rateLimiter(userId, limit = 100, window = 60) {
  const key = `ratelimit:${userId}`;
  const current = await redis.incr(key);

  if (current === 1) {
    await redis.expire(key, window); // 設定過期
  }

  if (current > limit) {
    throw new Error('Rate limit exceeded');
  }

  return true;
}
```

---

## Part 3: 資料庫設計進階

### 3.1 資料模型設計模式

#### 正規化 vs 反正規化

**第三正規化 (3NF) - 傳統關聯式設計**:

```sql
-- 完全正規化設計

-- Users 表
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  name VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Addresses 表（分離地址資訊）
CREATE TABLE addresses (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id) ON DELETE CASCADE,
  street VARCHAR(255),
  city VARCHAR(100),
  state VARCHAR(50),
  zip_code VARCHAR(10),
  country VARCHAR(50),
  type VARCHAR(20) -- 'billing' or 'shipping'
);

-- Orders 表
CREATE TABLE orders (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  billing_address_id INT REFERENCES addresses(id),
  shipping_address_id INT REFERENCES addresses(id),
  order_date TIMESTAMP DEFAULT NOW(),
  status VARCHAR(20)
);

-- Order Items 表（多對多關聯）
CREATE TABLE order_items (
  id SERIAL PRIMARY KEY,
  order_id INT REFERENCES orders(id) ON DELETE CASCADE,
  product_id INT REFERENCES products(id),
  quantity INT NOT NULL,
  price DECIMAL(10, 2) NOT NULL
);

-- Products 表
CREATE TABLE products (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  price DECIMAL(10, 2) NOT NULL,
  stock INT DEFAULT 0
);

-- 優勢：資料一致性高、無重複資料
-- 劣勢：查詢複雜（需多次 JOIN）、效能可能較差
```

**反正規化設計 - 效能優先**:

```sql
-- 反正規化設計（為了效能）

CREATE TABLE orders_denormalized (
  id SERIAL PRIMARY KEY,
  -- 使用者資訊（複製）
  user_id INT,
  user_name VARCHAR(255),
  user_email VARCHAR(255),

  -- 地址資訊（複製）
  billing_address JSONB,
  shipping_address JSONB,

  -- 訂單資訊
  order_date TIMESTAMP DEFAULT NOW(),
  status VARCHAR(20),

  -- Order Items（嵌入）
  items JSONB, -- [{ product_id, product_name, quantity, price }]

  -- 聚合資訊（預先計算）
  total_amount DECIMAL(10, 2),
  item_count INT
);

-- 優勢：單一查詢即可獲取所有資料、效能高
-- 劣勢：資料重複、更新複雜（需維護多處）
```

**混合策略（推薦）**:

```sql
-- 核心資料保持正規化
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  name VARCHAR(255) NOT NULL
);

CREATE TABLE orders (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  order_date TIMESTAMP DEFAULT NOW(),
  status VARCHAR(20),
  total DECIMAL(10, 2)
);

-- 高頻讀取資料使用 Materialized View（快取）
CREATE MATERIALIZED VIEW user_order_summary AS
SELECT
  u.id,
  u.name,
  u.email,
  COUNT(o.id) AS total_orders,
  SUM(o.total) AS total_spent,
  MAX(o.order_date) AS last_order_date
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
GROUP BY u.id, u.name, u.email;

-- 定期刷新 Materialized View
REFRESH MATERIALIZED VIEW user_order_summary;

-- 創建索引加速查詢
CREATE INDEX idx_user_order_summary_total_spent
ON user_order_summary(total_spent DESC);
```

### 3.2 資料庫分片 (Sharding)

```yaml
情境：應用成長到單一資料庫無法承載

分片策略選擇:

1. 水平分片（Horizontal Sharding）:
   - 按照某個鍵（如 user_id）將資料分散到多個資料庫
   - 每個分片擁有相同的 schema，但資料不重複

範例實作:
```javascript
// Node.js Sharding 邏輯

class ShardingManager {
  constructor(shards) {
    // shards = [ { id: 1, connection: 'postgres://shard1...' }, ... ]
    this.shards = shards;
    this.shardCount = shards.length;
  }

  // 一致性雜湊（Consistent Hashing）
  getShardId(userId) {
    const hash = this.hashFunction(userId);
    return hash % this.shardCount;
  }

  hashFunction(key) {
    // 簡單雜湊（實際應用應使用 CRC32, MurmurHash 等）
    let hash = 0;
    for (let i = 0; i < key.length; i++) {
      hash = ((hash << 5) - hash) + key.charCodeAt(i);
      hash = hash & hash; // Convert to 32bit integer
    }
    return Math.abs(hash);
  }

  async query(userId, sql, params) {
    const shardId = this.getShardId(userId);
    const shard = this.shards[shardId];
    return await shard.connection.query(sql, params);
  }

  async insert(userId, table, data) {
    const shardId = this.getShardId(userId);
    const shard = this.shards[shardId];
    return await shard.connection.insert(table, data);
  }
}

// 使用範例
const shardManager = new ShardingManager([
  { id: 1, connection: db1 },
  { id: 2, connection: db2 },
  { id: 3, connection: db3 }
]);

// 自動路由到正確的分片
const user = await shardManager.query(
  'user123',
  'SELECT * FROM users WHERE id = $1',
  ['user123']
);
```

挑戰與解決方案:

挑戰 1: 跨分片查詢（如全域排行榜）
解決方案:
  - 使用獨立的聚合資料庫（定期同步）
  - 使用搜尋引擎（Elasticsearch）
  - 實時聚合（查詢所有分片並合併結果）

挑戰 2: 分片再平衡（Rebalancing）
解決方案:
  - 使用虛擬節點（Virtual Nodes）減少遷移量
  - 雙寫策略（同時寫入舊分片和新分片）
  - 後台漸進式遷移

挑戰 3: 分散式交易
解決方案:
  - 避免跨分片交易（業務設計）
  - 使用 Saga 模式（補償機制）
  - 使用分散式交易協調器（2PC, TCC）
```

---

## Part 4: API 設計最佳實踐

### 4.1 RESTful API 設計原則

#### 資源命名和 HTTP 方法

```yaml
正確的 API 設計:

1. 資源命名（使用複數名詞）
   ✅ GET  /api/users          # 取得使用者列表
   ✅ GET  /api/users/123      # 取得單一使用者
   ✅ POST /api/users          # 建立使用者
   ✅ PUT  /api/users/123      # 完整更新使用者
   ✅ PATCH /api/users/123     # 部分更新使用者
   ✅ DELETE /api/users/123    # 刪除使用者

   ❌ GET  /api/getUser         # 避免動詞
   ❌ POST /api/createUser      # 避免動詞
   ❌ GET  /api/user/123        # 保持複數形式

2. 巢狀資源
   ✅ GET  /api/users/123/orders       # 取得使用者的訂單
   ✅ POST /api/users/123/orders       # 為使用者建立訂單
   ✅ GET  /api/users/123/orders/456   # 取得特定訂單

   ❌ GET  /api/orders?user_id=123     # 過度巢狀時可使用查詢參數

3. 查詢參數
   ✅ GET  /api/products?category=electronics&sort=price&order=asc&limit=20&offset=40

   標準參數:
   - 分頁: limit, offset (或 page, per_page)
   - 排序: sort, order
   - 過濾: field=value
   - 搜尋: q=keyword
   - 欄位選擇: fields=name,price

4. HTTP 狀態碼
   成功:
   - 200 OK: 成功（GET, PUT, PATCH, DELETE）
   - 201 Created: 資源已建立（POST）
   - 204 No Content: 成功但無回應內容（DELETE）

   客戶端錯誤:
   - 400 Bad Request: 請求格式錯誤
   - 401 Unauthorized: 未認證
   - 403 Forbidden: 已認證但無權限
   - 404 Not Found: 資源不存在
   - 409 Conflict: 資源衝突（如重複建立）
   - 422 Unprocessable Entity: 驗證失敗

   伺服器錯誤:
   - 500 Internal Server Error: 伺服器錯誤
   - 503 Service Unavailable: 服務暫時無法使用
```

#### 完整 API 範例（Node.js + Express）

```javascript
const express = require('express');
const app = express();

// Middleware
app.use(express.json());
app.use(require('cors')());

// 錯誤處理類別
class APIError extends Error {
  constructor(status, message, details = null) {
    super(message);
    this.status = status;
    this.details = details;
  }
}

// 驗證 Middleware
function validateUser(req, res, next) {
  const { name, email } = req.body;
  const errors = [];

  if (!name || name.length < 2) {
    errors.push({ field: 'name', message: 'Name must be at least 2 characters' });
  }

  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    errors.push({ field: 'email', message: 'Invalid email format' });
  }

  if (errors.length > 0) {
    return next(new APIError(422, 'Validation failed', errors));
  }

  next();
}

// 分頁輔助函數
function paginate(req) {
  const page = parseInt(req.query.page) || 1;
  const perPage = parseInt(req.query.per_page) || 20;
  const offset = (page - 1) * perPage;

  return { limit: perPage, offset, page };
}

// Routes

// 1. 列表（帶分頁、過濾、排序）
app.get('/api/users', async (req, res, next) => {
  try {
    const { limit, offset, page } = paginate(req);
    const { sort = 'created_at', order = 'desc', search } = req.query;

    let query = db.users.query();

    // 搜尋
    if (search) {
      query = query.where('name', 'ILIKE', `%${search}%`);
    }

    // 排序
    query = query.orderBy(sort, order);

    // 分頁
    const total = await query.clone().count();
    const users = await query.limit(limit).offset(offset);

    res.json({
      data: users,
      meta: {
        page,
        per_page: limit,
        total: total[0].count,
        total_pages: Math.ceil(total[0].count / limit)
      },
      links: {
        self: `/api/users?page=${page}&per_page=${limit}`,
        next: `/api/users?page=${page + 1}&per_page=${limit}`,
        prev: page > 1 ? `/api/users?page=${page - 1}&per_page=${limit}` : null
      }
    });
  } catch (error) {
    next(error);
  }
});

// 2. 取得單一資源
app.get('/api/users/:id', async (req, res, next) => {
  try {
    const user = await db.users.findOne(req.params.id);

    if (!user) {
      throw new APIError(404, 'User not found');
    }

    res.json({ data: user });
  } catch (error) {
    next(error);
  }
});

// 3. 建立資源
app.post('/api/users', validateUser, async (req, res, next) => {
  try {
    const { name, email, password } = req.body;

    // 檢查重複
    const existing = await db.users.findOne({ email });
    if (existing) {
      throw new APIError(409, 'User with this email already exists');
    }

    // 建立使用者
    const user = await db.users.create({
      name,
      email,
      password: await hashPassword(password)
    });

    res.status(201).json({
      data: user,
      message: 'User created successfully'
    });
  } catch (error) {
    next(error);
  }
});

// 4. 更新資源（部分更新）
app.patch('/api/users/:id', async (req, res, next) => {
  try {
    const user = await db.users.findOne(req.params.id);

    if (!user) {
      throw new APIError(404, 'User not found');
    }

    // 只更新提供的欄位
    const allowedFields = ['name', 'email', 'avatar'];
    const updates = {};

    for (const field of allowedFields) {
      if (req.body[field] !== undefined) {
        updates[field] = req.body[field];
      }
    }

    const updatedUser = await db.users.update(req.params.id, updates);

    res.json({
      data: updatedUser,
      message: 'User updated successfully'
    });
  } catch (error) {
    next(error);
  }
});

// 5. 刪除資源
app.delete('/api/users/:id', async (req, res, next) => {
  try {
    const user = await db.users.findOne(req.params.id);

    if (!user) {
      throw new APIError(404, 'User not found');
    }

    await db.users.delete(req.params.id);

    res.status(204).send(); // No Content
  } catch (error) {
    next(error);
  }
});

// 全域錯誤處理
app.use((err, req, res, next) => {
  console.error('API Error:', err);

  if (err instanceof APIError) {
    return res.status(err.status).json({
      error: {
        message: err.message,
        status: err.status,
        details: err.details
      }
    });
  }

  // 未預期的錯誤
  res.status(500).json({
    error: {
      message: 'Internal server error',
      status: 500
    }
  });
});

app.listen(3000);
```

### 4.2 API 版本控制

```yaml
版本控制策略:

策略 1: URL Path Versioning（推薦）
✅ /api/v1/users
✅ /api/v2/users

優勢:
  - 清晰明確
  - 易於路由和快取
  - 不同版本可獨立部署

劣勢:
  - URL 變更

策略 2: Header Versioning
✅ GET /api/users
   Accept: application/vnd.myapi.v1+json

優勢:
  - URL 保持不變
  - 符合 REST 原則

劣勢:
  - 不易察覺版本
  - 快取複雜

策略 3: Query Parameter Versioning
✅ /api/users?version=1

優勢:
  - 簡單

劣勢:
  - 容易被忽略
  - 快取複雜

推薦策略: URL Path + 語意化版本號
/api/v1/users
/api/v2/users

版本升級規則（遵循 Semver）:
  - v1 → v2: Breaking changes（不向後兼容）
  - v2.0 → v2.1: 新功能（向後兼容）
  - v2.1.0 → v2.1.1: Bug fixes（向後兼容）

實作範例:
```javascript
// routes/v1/users.js
const express = require('express');
const router = express.Router();

router.get('/', async (req, res) => {
  // v1 實作
  const users = await db.users.find({}, { password: 0 });
  res.json(users);
});

module.exports = router;

// routes/v2/users.js
const express = require('express');
const router = express.Router();

router.get('/', async (req, res) => {
  // v2 實作（新增分頁、過濾功能）
  const { page = 1, limit = 20, role } = req.query;
  const offset = (page - 1) * limit;

  let query = db.users.query().select('id', 'name', 'email', 'role');

  if (role) {
    query = query.where('role', role);
  }

  const users = await query.limit(limit).offset(offset);
  const total = await db.users.count();

  res.json({
    data: users,
    pagination: {
      page,
      limit,
      total
    }
  });
});

module.exports = router;

// app.js
const app = express();

app.use('/api/v1/users', require('./routes/v1/users'));
app.use('/api/v2/users', require('./routes/v2/users'));
```

版本淘汰政策:
  1. 宣布棄用（Deprecated）: 至少提前 6 個月
  2. 在回應中添加警告 Header:
     `Deprecation: version="v1", date="2024-12-31"`
  3. 提供遷移指南
  4. 保留至少 2 個主要版本
```

---

## Part 5: 前端架構策略

### 5.1 狀態管理選擇

#### Redux vs Zustand vs Recoil vs Context API

**Redux (傳統方案 - 大型應用)**:

```javascript
// Redux Toolkit (現代 Redux)

// store/slices/userSlice.js
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';

// Async Thunk (處理非同步邏輯)
export const fetchUsers = createAsyncThunk(
  'users/fetchUsers',
  async (_, { rejectWithValue }) => {
    try {
      const response = await fetch('/api/users');
      return response.json();
    } catch (error) {
      return rejectWithValue(error.message);
    }
  }
);

const userSlice = createSlice({
  name: 'users',
  initialState: {
    list: [],
    loading: false,
    error: null,
    currentUser: null
  },
  reducers: {
    setCurrentUser: (state, action) => {
      state.currentUser = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    }
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchUsers.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchUsers.fulfilled, (state, action) => {
        state.loading = false;
        state.list = action.payload;
      })
      .addCase(fetchUsers.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });
  }
});

export const { setCurrentUser, clearError } = userSlice.actions;
export default userSlice.reducer;

// store/index.js
import { configureStore } from '@reduxjs/toolkit';
import userReducer from './slices/userSlice';

export const store = configureStore({
  reducer: {
    users: userReducer
  }
});

// Component
import { useSelector, useDispatch } from 'react-redux';
import { fetchUsers, setCurrentUser } from './store/slices/userSlice';

function UserList() {
  const dispatch = useDispatch();
  const { list, loading, error } = useSelector(state => state.users);

  useEffect(() => {
    dispatch(fetchUsers());
  }, [dispatch]);

  if (loading) return <Spinner />;
  if (error) return <Error message={error} />;

  return (
    <ul>
      {list.map(user => (
        <li key={user.id} onClick={() => dispatch(setCurrentUser(user))}>
          {user.name}
        </li>
      ))}
    </ul>
  );
}
```

**Zustand (簡潔方案 - 推薦)**:

```javascript
// store/useUserStore.js
import create from 'zustand';
import { devtools, persist } from 'zustand/middleware';

export const useUserStore = create(
  devtools(
    persist(
      (set, get) => ({
        // State
        users: [],
        currentUser: null,
        loading: false,
        error: null,

        // Actions
        fetchUsers: async () => {
          set({ loading: true });
          try {
            const response = await fetch('/api/users');
            const users = await response.json();
            set({ users, loading: false });
          } catch (error) {
            set({ error: error.message, loading: false });
          }
        },

        setCurrentUser: (user) => set({ currentUser: user }),

        updateUser: async (id, updates) => {
          try {
            const response = await fetch(`/api/users/${id}`, {
              method: 'PATCH',
              body: JSON.stringify(updates)
            });
            const updatedUser = await response.json();

            // 更新 users 列表
            set(state => ({
              users: state.users.map(u => u.id === id ? updatedUser : u)
            }));
          } catch (error) {
            set({ error: error.message });
          }
        },

        // Computed (使用 get())
        getUserById: (id) => {
          return get().users.find(u => u.id === id);
        }
      }),
      {
        name: 'user-storage', // LocalStorage key
        getStorage: () => localStorage
      }
    )
  )
);

// Component
function UserList() {
  const { users, loading, error, fetchUsers, setCurrentUser } = useUserStore();

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  if (loading) return <Spinner />;
  if (error) return <Error message={error} />;

  return (
    <ul>
      {users.map(user => (
        <li key={user.id} onClick={() => setCurrentUser(user)}>
          {user.name}
        </li>
      ))}
    </ul>
  );
}
```

### 5.2 程式碼分割和延遲載入

```javascript
// React Code Splitting

// 1. Route-based Code Splitting
import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';

// 懶載入元件
const Home = lazy(() => import('./pages/Home'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Profile = lazy(() => import('./pages/Profile'));

function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<LoadingPage />}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/profile" element={<Profile />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

// 2. Component-based Code Splitting
const HeavyChart = lazy(() => import('./components/HeavyChart'));

function Dashboard() {
  const [showChart, setShowChart] = useState(false);

  return (
    <div>
      <h1>Dashboard</h1>
      <button onClick={() => setShowChart(true)}>Show Chart</button>

      {showChart && (
        <Suspense fallback={<Spinner />}>
          <HeavyChart />
        </Suspense>
      )}
    </div>
  );
}

// 3. 預載入（Preload）
function Homepage() {
  // 滑鼠 hover 時預載入 Dashboard
  const handleMouseEnter = () => {
    import('./pages/Dashboard'); // 觸發預載入
  };

  return (
    <div>
      <Link
        to="/dashboard"
        onMouseEnter={handleMouseEnter}
      >
        Go to Dashboard
      </Link>
    </div>
  );
}

// 4. 動態匯入（條件載入）
async function loadEditor() {
  if (userHasPremium) {
    const { AdvancedEditor } = await import('./components/AdvancedEditor');
    return AdvancedEditor;
  } else {
    const { BasicEditor } = await import('./components/BasicEditor');
    return BasicEditor;
  }
}
```

---

## Part 6: CI/CD 與 DevOps

### 6.1 完整 CI/CD Pipeline

**GitHub Actions 範例**:

```yaml
# .github/workflows/ci-cd.yml

name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  # Job 1: 測試
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run linter
        run: npm run lint

      - name: Run tests
        run: npm test
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage/lcov.info

  # Job 2: 建置 Docker Image
  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Login to Docker Hub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}

      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: myapp/backend:${{ github.sha }},myapp/backend:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # Job 3: 部署到 Staging
  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    environment: staging

    steps:
      - name: Deploy to Staging
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.STAGING_HOST }}
          username: ${{ secrets.STAGING_USER }}
          key: ${{ secrets.STAGING_SSH_KEY }}
          script: |
            cd /app
            docker-compose pull
            docker-compose up -d
            docker-compose exec -T web npm run migrate

      - name: Run smoke tests
        run: npm run test:smoke
        env:
          API_URL: https://staging.myapp.com

  # Job 4: 部署到 Production（需手動批准）
  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production

    steps:
      - name: Deploy to Production
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.PROD_HOST }}
          username: ${{ secrets.PROD_USER }}
          key: ${{ secrets.PROD_SSH_KEY }}
          script: |
            cd /app
            docker-compose pull
            docker-compose up -d --no-deps backend
            docker-compose exec -T web npm run migrate

      - name: Notify Slack
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: 'Production deployment completed!'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

**Dockerfile 最佳實踐**:

```dockerfile
# Multi-stage build

# Stage 1: Dependencies
FROM node:18-alpine AS deps
WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

# Stage 2: Build
FROM node:18-alpine AS build
WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 3: Production
FROM node:18-alpine AS production
WORKDIR /app

# 安全性：使用非 root 使用者
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nodejs -u 1001

# 只複製必要檔案
COPY --from=deps --chown=nodejs:nodejs /app/node_modules ./node_modules
COPY --from=build --chown=nodejs:nodejs /app/dist ./dist
COPY --chown=nodejs:nodejs package.json ./

USER nodejs

EXPOSE 3000

CMD ["node", "dist/index.js"]
```

**Docker Compose (本地開發)**:

```yaml
# docker-compose.yml

version: '3.8'

services:
  backend:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=development
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/myapp
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./src:/app/src # Hot reload
    depends_on:
      - db
      - redis

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=myapp
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  frontend:
    image: node:18-alpine
    working_dir: /app
    command: npm run dev
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
    environment:
      - VITE_API_URL=http://localhost:3000

volumes:
  postgres_data:
```

---

## Part 7: 效能與擴展性

### 7.1 前端效能優化

```javascript
// 1. 防抖動和節流

// Debounce（使用者停止輸入後才執行）
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// 搜尋輸入範例
const handleSearch = debounce((query) => {
  fetch(`/api/search?q=${query}`)
    .then(res => res.json())
    .then(results => setResults(results));
}, 300);

// Throttle（限制執行頻率）
function throttle(func, limit) {
  let inThrottle;
  return function(...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

// Scroll 事件範例
const handleScroll = throttle(() => {
  console.log('Scrolling...');
  // 更新 UI
}, 100);

window.addEventListener('scroll', handleScroll);

// 2. 虛擬滾動（處理大量列表）
import { FixedSizeList } from 'react-window';

function VirtualizedList({ items }) {
  const Row = ({ index, style }) => (
    <div style={style}>
      {items[index].name}
    </div>
  );

  return (
    <FixedSizeList
      height={600}
      itemCount={items.length}
      itemSize={50}
      width="100%"
    >
      {Row}
    </FixedSizeList>
  );
}

// 3. 圖片延遲載入
<img
  src="placeholder.jpg"
  data-src="actual-image.jpg"
  loading="lazy"
  alt="Description"
/>

// Intersection Observer API
const images = document.querySelectorAll('img[data-src]');

const imageObserver = new IntersectionObserver((entries, observer) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const img = entry.target;
      img.src = img.dataset.src;
      img.removeAttribute('data-src');
      observer.unobserve(img);
    }
  });
});

images.forEach(img => imageObserver.observe(img));

// 4. Web Workers（CPU 密集型任務）

// worker.js
self.addEventListener('message', (e) => {
  const { data } = e;

  // 執行複雜計算
  const result = heavyComputation(data);

  self.postMessage(result);
});

// main.js
const worker = new Worker('worker.js');

worker.postMessage(largeDataset);

worker.addEventListener('message', (e) => {
  console.log('Result:', e.data);
});
```

### 7.2 後端效能優化

```javascript
// 1. 資料庫查詢優化

// ❌ N+1 問題
const users = await User.findAll();
for (const user of users) {
  const orders = await Order.findAll({ where: { userId: user.id } }); // N 次查詢
}

// ✅ Eager Loading（一次查詢）
const users = await User.findAll({
  include: [{ model: Order }]
});

// ✅ DataLoader（自動批次處理）
const DataLoader = require('dataloader');

const userLoader = new DataLoader(async (userIds) => {
  const users = await User.findAll({
    where: { id: userIds }
  });

  // 返回排序正確的結果
  return userIds.map(id => users.find(u => u.id === id));
});

// 使用
const user1 = await userLoader.load(1);
const user2 = await userLoader.load(2); // 自動合併成一次查詢

// 2. 快取策略

const redis = require('redis').createClient();

// Cache-Aside Pattern
async function getUser(userId) {
  const cacheKey = `user:${userId}`;

  // 1. 檢查快取
  const cached = await redis.get(cacheKey);
  if (cached) {
    return JSON.parse(cached);
  }

  // 2. 查詢資料庫
  const user = await db.users.findOne(userId);

  // 3. 寫入快取
  await redis.setex(cacheKey, 3600, JSON.stringify(user));

  return user;
}

// Cache invalidation（資料更新時清除快取）
async function updateUser(userId, updates) {
  const user = await db.users.update(userId, updates);

  // 清除相關快取
  await redis.del(`user:${userId}`);

  return user;
}

// 3. HTTP 快取

app.get('/api/products/:id', async (req, res) => {
  const product = await db.products.findOne(req.params.id);

  // 設定快取 Headers
  res.set({
    'Cache-Control': 'public, max-age=3600', // 瀏覽器快取 1 小時
    'ETag': generateETag(product),
    'Last-Modified': product.updatedAt
  });

  res.json(product);
});

// 4. 資料庫連線池

const { Pool } = require('pg');

const pool = new Pool({
  host: 'localhost',
  database: 'myapp',
  user: 'postgres',
  password: 'password',
  max: 20, // 最大連線數
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000
});

// 使用
async function query(sql, params) {
  const client = await pool.connect();
  try {
    const result = await client.query(sql, params);
    return result.rows;
  } finally {
    client.release(); // 返回連線池
  }
}
```

---

## Part 8: 安全性設計

### 8.1 認證與授權

**JWT 認證實作**:

```javascript
const jwt = require('jsonwebtoken');
const bcrypt = require('bcrypt');

// 註冊
app.post('/api/auth/register', async (req, res) => {
  const { email, password } = req.body;

  // 驗證輸入
  if (!email || !password) {
    return res.status(400).json({ error: 'Email and password required' });
  }

  // 檢查重複
  const existing = await db.users.findOne({ email });
  if (existing) {
    return res.status(409).json({ error: 'Email already registered' });
  }

  // 雜湊密碼
  const hashedPassword = await bcrypt.hash(password, 10);

  // 建立使用者
  const user = await db.users.create({
    email,
    password: hashedPassword
  });

  res.status(201).json({ message: 'User created successfully' });
});

// 登入
app.post('/api/auth/login', async (req, res) => {
  const { email, password } = req.body;

  // 查詢使用者
  const user = await db.users.findOne({ email });
  if (!user) {
    return res.status(401).json({ error: 'Invalid credentials' });
  }

  // 驗證密碼
  const valid = await bcrypt.compare(password, user.password);
  if (!valid) {
    return res.status(401).json({ error: 'Invalid credentials' });
  }

  // 生成 JWT
  const accessToken = jwt.sign(
    { userId: user.id, email: user.email, role: user.role },
    process.env.JWT_SECRET,
    { expiresIn: '15m' }
  );

  const refreshToken = jwt.sign(
    { userId: user.id },
    process.env.JWT_REFRESH_SECRET,
    { expiresIn: '7d' }
  );

  // 儲存 refresh token
  await db.refreshTokens.create({
    userId: user.id,
    token: refreshToken,
    expiresAt: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)
  });

  res.json({
    accessToken,
    refreshToken,
    user: {
      id: user.id,
      email: user.email,
      name: user.name
    }
  });
});

// 驗證 Middleware
function authenticateToken(req, res, next) {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1]; // Bearer TOKEN

  if (!token) {
    return res.status(401).json({ error: 'Access token required' });
  }

  jwt.verify(token, process.env.JWT_SECRET, (err, user) => {
    if (err) {
      return res.status(403).json({ error: 'Invalid or expired token' });
    }

    req.user = user;
    next();
  });
}

// 授權 Middleware (RBAC)
function authorizeRole(...roles) {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    if (!roles.includes(req.user.role)) {
      return res.status(403).json({ error: 'Forbidden: insufficient permissions' });
    }

    next();
  };
}

// 使用範例
app.get('/api/admin/users',
  authenticateToken,
  authorizeRole('admin', 'superadmin'),
  async (req, res) => {
    const users = await db.users.findAll();
    res.json(users);
  }
);

// Refresh Token
app.post('/api/auth/refresh', async (req, res) => {
  const { refreshToken } = req.body;

  if (!refreshToken) {
    return res.status(401).json({ error: 'Refresh token required' });
  }

  // 驗證 refresh token
  let payload;
  try {
    payload = jwt.verify(refreshToken, process.env.JWT_REFRESH_SECRET);
  } catch (err) {
    return res.status(403).json({ error: 'Invalid refresh token' });
  }

  // 檢查資料庫中是否存在
  const stored = await db.refreshTokens.findOne({ token: refreshToken });
  if (!stored || stored.expiresAt < new Date()) {
    return res.status(403).json({ error: 'Refresh token expired' });
  }

  // 生成新的 access token
  const user = await db.users.findOne(payload.userId);
  const accessToken = jwt.sign(
    { userId: user.id, email: user.email, role: user.role },
    process.env.JWT_SECRET,
    { expiresIn: '15m' }
  );

  res.json({ accessToken });
});
```

### 8.2 常見安全漏洞防範

```javascript
// 1. SQL Injection 防範（使用 Parameterized Queries）

// ❌ 危險
const userId = req.query.id;
const sql = `SELECT * FROM users WHERE id = ${userId}`; // SQL Injection 風險！

// ✅ 安全
const sql = 'SELECT * FROM users WHERE id = $1';
const result = await db.query(sql, [userId]);

// 2. XSS (Cross-Site Scripting) 防範

// ❌ 危險
app.get('/search', (req, res) => {
  const query = req.query.q;
  res.send(`<h1>Results for: ${query}</h1>`); // XSS 風險！
});

// ✅ 安全（使用模板引擎自動轉義）
app.set('view engine', 'ejs');
app.get('/search', (req, res) => {
  res.render('search', { query: req.query.q }); // EJS 會自動轉義
});

// 前端也要轉義
function escapeHTML(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// 3. CSRF (Cross-Site Request Forgery) 防範

const csrf = require('csurf');
const csrfProtection = csrf({ cookie: true });

app.get('/form', csrfProtection, (req, res) => {
  res.render('form', { csrfToken: req.csrfToken() });
});

app.post('/submit', csrfProtection, (req, res) => {
  // CSRF token 會自動驗證
  res.send('Data submitted');
});

// 4. Rate Limiting（防止暴力破解）

const rateLimit = require('express-rate-limit');

const loginLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 分鐘
  max: 5, // 最多 5 次嘗試
  message: 'Too many login attempts, please try again later',
  standardHeaders: true,
  legacyHeaders: false
});

app.post('/api/auth/login', loginLimiter, async (req, res) => {
  // 登入邏輯
});

// 5. 輸入驗證

const Joi = require('joi');

const userSchema = Joi.object({
  email: Joi.string().email().required(),
  password: Joi.string().min(8).required(),
  age: Joi.number().integer().min(18).max(120)
});

app.post('/api/users', (req, res) => {
  const { error, value } = userSchema.validate(req.body);

  if (error) {
    return res.status(400).json({
      error: 'Validation failed',
      details: error.details.map(d => d.message)
    });
  }

  // 使用經過驗證的資料
  createUser(value);
});

// 6. Helmet.js（設定安全 Headers）

const helmet = require('helmet');
app.use(helmet());

// 等同於設定以下 Headers:
// - X-DNS-Prefetch-Control
// - X-Frame-Options
// - X-Content-Type-Options
// - Strict-Transport-Security
// - X-Download-Options
// - X-Permitted-Cross-Domain-Policies
```

---

## Part 9: Troubleshooting Guide

### 9.1 常見問題診斷

**問題 1: 資料庫連線池耗盡**

```yaml
症狀:
  - Error: "Connection pool exhausted"
  - 請求超時
  - 資料庫 CPU 使用率高

診斷步驟:
  1. 檢查連線池配置
     SELECT count(*) FROM pg_stat_activity; -- PostgreSQL
     SHOW PROCESSLIST; -- MySQL

  2. 檢查是否有未釋放的連線
     // 確保使用 try-finally
     const client = await pool.connect();
     try {
       await client.query(...);
     } finally {
       client.release(); // 必須！
     }

  3. 檢查是否有長時間執行的查詢
     SELECT pid, now() - query_start AS duration, query
     FROM pg_stat_activity
     WHERE state = 'active'
     ORDER BY duration DESC;

解決方案:
  - 增加連線池大小（但不要無限增加）
  - 設定合理的 timeout
  - 使用連線池監控
  - 優化慢查詢

範例監控:
```javascript
pool.on('error', (err, client) => {
  console.error('Unexpected error on idle client', err);
});

pool.on('connect', () => {
  console.log('New client connected to pool');
});

setInterval(async () => {
  console.log('Pool stats:', {
    total: pool.totalCount,
    idle: pool.idleCount,
    waiting: pool.waitingCount
  });
}, 60000);
```
```

**問題 2: 記憶體洩漏**

```yaml
症狀:
  - Node.js 程序記憶體持續增長
  - 最終 OOM (Out of Memory) 崩潰

診斷工具:
```javascript
// 使用 clinic.js
npm install -g clinic
clinic doctor -- node app.js

// 使用 heapdump
const heapdump = require('heapdump');

app.get('/heapdump', (req, res) => {
  heapdump.writeSnapshot((err, filename) => {
    res.send(`Heap dump written to ${filename}`);
  });
});

// 使用 Chrome DevTools 分析 heap snapshot
```

常見原因:
  1. 全域變數累積
  2. 事件監聽器未移除
  3. 定時器未清除
  4. 快取無限增長

解決方案:
```javascript
// ❌ 記憶體洩漏
const cache = {}; // 無限增長

app.get('/user/:id', (req, res) => {
  cache[req.params.id] = fetchUser(req.params.id); // 洩漏！
});

// ✅ 使用 LRU Cache
const LRU = require('lru-cache');
const cache = new LRU({
  max: 500, // 最多 500 個項目
  maxAge: 1000 * 60 * 60 // 1 小時過期
});

// ❌ 事件監聽器洩漏
setInterval(() => {
  eventEmitter.on('data', handler); // 每次都加新的監聽器！
}, 1000);

// ✅ 正確移除
const handler = (data) => { /* ... */ };
eventEmitter.on('data', handler);

// 稍後移除
eventEmitter.off('data', handler);
```
```

**問題 3: API 效能緩慢**

```yaml
診斷工具:
  1. APM (Application Performance Monitoring)
     - New Relic
     - Datadog
     - Elastic APM

  2. 請求追蹤
```javascript
// 使用 express-pino-logger
const pino = require('pino');
const expressPino = require('express-pino-logger');

const logger = pino({ level: 'info' });
app.use(expressPino({ logger }));

// 每個請求會自動記錄:
// { req: { method, url }, res: { statusCode }, responseTime }

// 手動追蹤慢查詢
async function queryWithTiming(sql, params) {
  const start = Date.now();
  const result = await db.query(sql, params);
  const duration = Date.now() - start;

  if (duration > 1000) { // > 1 秒
    logger.warn({
      type: 'slow_query',
      sql,
      duration
    });
  }

  return result;
}
```

常見瓶頸:
  1. N+1 查詢問題 → 使用 DataLoader 或 Eager Loading
  2. 缺少資料庫索引 → EXPLAIN ANALYZE
  3. 同步阻塞操作 → 改用非同步
  4. 過大的回應 → 分頁、欄位選擇
```

---

## Part 10: 真實案例研究

### Case Study: 電商平台從 Monolith 到 Microservices

**背景**:
- 初期: Rails Monolith（5 人團隊，1 萬使用者）
- 成長: 20 人團隊，50 萬使用者，效能瓶頸出現
- 目標: 拆分為微服務，支援 100 萬+ 使用者

**架構演進**:

```yaml
Phase 1: Monolith (Year 1-2)
  Ruby on Rails + PostgreSQL + Redis

  優勢: 快速開發、部署簡單
  劣勢: 部署風險高、擴展困難

Phase 2: 垂直分割 (Year 2-3)
  拆分出第一個微服務: Payment Service

  原因: 付款邏輯複雜、需要獨立擴展、PCI 合規要求

  架構:
    - Rails Monolith (核心業務)
    - Node.js Payment Service (獨立)
    - 通訊: REST API

Phase 3: 持續拆分 (Year 3-4)
  新增微服務:
    - Order Service (Node.js)
    - Inventory Service (Go)
    - Notification Service (Python)
    - Search Service (Elasticsearch)

  架構:
    - API Gateway (Kong)
    - Service Mesh (Istio)
    - Message Queue (RabbitMQ)
    - Event Store (Kafka)

Phase 4: 完全微服務化 (Year 4+)
  所有核心功能獨立服務
```

**關鍵決策與經驗**:

```yaml
決策 1: 選擇拆分順序
  策略: Strangler Fig Pattern

  1. 識別邊界清晰的模組 → Payment
  2. 高流量服務優先 → Search, Product Catalog
  3. 獨立業務邏輯 → Recommendation Engine

決策 2: 資料庫策略
  問題: 共用資料庫 vs 獨立資料庫？

  選擇: 每個服務獨立資料庫

  挑戰: 資料一致性
  解決: Event Sourcing + CQRS

  範例:
```javascript
// Order Service 發布事件
await eventBus.publish('order.created', {
  orderId: 'order123',
  userId: 'user456',
  items: [...],
  total: 100
});

// Inventory Service 監聽並更新庫存
eventBus.subscribe('order.created', async (event) => {
  for (const item of event.items) {
    await inventory.decreaseStock(item.productId, item.quantity);
  }
});

// Notification Service 監聽並發送通知
eventBus.subscribe('order.created', async (event) => {
  await sendEmail(event.userId, 'Order Confirmation', event);
});
```

決策 3: API Gateway
  選擇: Kong API Gateway

  優勢:
    - 統一入口
    - 速率限制
    - 認證授權
    - 請求路由

  配置範例:
```yaml
# Kong 路由配置
services:
  - name: order-service
    url: http://order-service:3000
    routes:
      - name: orders-route
        paths:
          - /api/orders

plugins:
  - name: rate-limiting
    config:
      minute: 100
      policy: local
  - name: jwt
    config:
      secret_is_base64: false
```

成果:
  - API 回應時間: 從 500ms 降至 100ms (P95)
  - 部署頻率: 從每週一次提升到每天 10+ 次
  - 服務可用性: 從 99.5% 提升到 99.95%
  - 團隊自主性: 各團隊獨立開發、部署
```

---

## 總結

本深度技術指南涵蓋了 Greenfield 新專案開發的進階主題:

✅ **技術選型深度分析**（前端、後端、資料庫全方位對比）
✅ **架構設計模式**（Monolith vs Microservices vs Serverless）
✅ **資料庫設計進階**（正規化、分片、索引優化）
✅ **API 設計最佳實踐**（RESTful、版本控制、錯誤處理）
✅ **前端架構策略**（狀態管理、程式碼分割、效能優化）
✅ **CI/CD 與 DevOps**（GitHub Actions、Docker、部署策略）
✅ **效能與擴展性**（快取、資料庫優化、負載均衡）
✅ **安全性設計**（認證授權、漏洞防範、最佳實踐）
✅ **Troubleshooting Guide**（常見問題診斷與解決）
✅ **真實案例研究**（電商平台架構演進經驗）

---

## 📚 延伸閱讀

- [System Design Primer](https://github.com/donnemartin/system-design-primer)
- [The Twelve-Factor App](https://12factor.net/)
- [Microservices Patterns](https://microservices.io/patterns/)
- [Web Performance Best Practices](https://web.dev/fast/)
- [OWASP Top Ten](https://owasp.org/www-project-top-ten/)

---

**文檔版本: v0.01
**最後更新**: 2026-02-15
**維護者**: AISDLC Framework Team
