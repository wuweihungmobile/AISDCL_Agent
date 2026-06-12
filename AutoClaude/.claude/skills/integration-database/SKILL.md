---
name: integration-database
description: 整合資料庫服務，包含 PostgreSQL、MySQL、MongoDB，支援 Prisma ORM (Node.js) 和 Spring Data JPA (Java)
user-invocable: true
disable-model-invocation: false
argument-hint: "<database: 資料庫類型 (postgres/mysql/mongodb)> [orm: ORM 工具 (prisma/drizzle/typeorm/jpa/hibernate)]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
  - Bash
---

# Integration Database Skill

整合資料庫和 ORM 服務。

---

## 觸發方式

```bash
/integration-database postgres           # PostgreSQL + Prisma (Node.js)
/integration-database postgres jpa       # PostgreSQL + Spring Data JPA (Java)
/integration-database mysql drizzle      # MySQL + Drizzle
/integration-database mongodb            # MongoDB
```

---

## 執行流程

### 階段 1: 資料庫設定 🔴

**確認項目**:
- [ ] 資料庫類型選擇
- [ ] 連線資訊
- [ ] ORM 工具選擇
- [ ] 資料模型設計

**環境變數**:
```env
DATABASE_URL="postgresql://user:password@localhost:5432/mydb?schema=public"
```

🔴 **確認點**: 確認資料庫配置

---

### 階段 2A: Spring Data JPA 設定 (Java/Spring Boot + PostgreSQL)

> 當 ORM 選擇為 `jpa` 或 `hibernate` 時使用此階段

**build.gradle.kts 依賴**:
```kotlin
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    implementation("org.springframework.boot:spring-boot-starter-validation")
    runtimeOnly("org.postgresql:postgresql")
    implementation("org.flywaydb:flyway-core")
    implementation("org.flywaydb:flyway-database-postgresql")
    testImplementation("org.testcontainers:postgresql")
    testImplementation("org.testcontainers:junit-jupiter")
}
```

**application.yml 配置**:
```yaml
spring:
  datasource:
    url: jdbc:postgresql://${DB_HOST:localhost}:${DB_PORT:5432}/${DB_NAME:mydb}
    username: ${DB_USERNAME:postgres}
    password: ${DB_PASSWORD:secret}
    hikari:
      maximum-pool-size: 20
      minimum-idle: 5
  jpa:
    hibernate:
      ddl-auto: validate  # 生產環境使用 validate，由 Flyway 管理 schema
    open-in-view: false
    properties:
      hibernate:
        format_sql: true
        default_batch_fetch_size: 20
  flyway:
    enabled: true
    locations: classpath:db/migration
```

**Entity 範例**:
```java
@Entity
@Table(name = "products")
public class Product {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 200)
    private String name;

    @Column(nullable = false, unique = true, length = 50)
    private String sku;

    @Column(nullable = false, precision = 12, scale = 2)
    private BigDecimal price;

    @Column(nullable = false)
    private Integer stockQuantity;

    @Column(length = 500)
    private String barcode;  // 條碼掃描用

    @CreatedDate
    private LocalDateTime createdAt;

    @LastModifiedDate
    private LocalDateTime updatedAt;
}
```

**Repository 範例**:
```java
public interface ProductRepository extends JpaRepository<Product, Long> {
    Optional<Product> findBySku(String sku);
    Optional<Product> findByBarcode(String barcode);
    List<Product> findByStockQuantityLessThan(int threshold);

    @Query("SELECT p FROM Product p WHERE p.name LIKE %:keyword% OR p.sku LIKE %:keyword%")
    Page<Product> search(@Param("keyword") String keyword, Pageable pageable);
}
```

**Flyway 遷移範例** (`src/main/resources/db/migration/V1__init.sql`):
```sql
CREATE TABLE products (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    sku VARCHAR(50) NOT NULL UNIQUE,
    price NUMERIC(12, 2) NOT NULL,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    barcode VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_products_barcode ON products(barcode);
```

**Testcontainers 整合測試**:
```java
@SpringBootTest
@Testcontainers
class ProductRepositoryTest {
    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:18-alpine");

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }

    @Autowired
    private ProductRepository productRepository;

    @Test
    void shouldFindByBarcode() {
        // given
        Product product = new Product();
        product.setName("Test Product");
        product.setSku("SKU-001");
        product.setBarcode("4901234567890");
        product.setPrice(new BigDecimal("99.99"));
        product.setStockQuantity(100);
        productRepository.save(product);

        // when
        Optional<Product> found = productRepository.findByBarcode("4901234567890");

        // then
        assertThat(found).isPresent();
        assertThat(found.get().getSku()).isEqualTo("SKU-001");
    }
}
```

---

### 階段 2B: Prisma 設定 (PostgreSQL)

```bash
# 安裝
npm install prisma @prisma/client
npx prisma init
```

```prisma
// prisma/schema.prisma
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

// 使用者模型
model User {
  id        String   @id @default(cuid())
  email     String   @unique
  name      String?
  password  String
  role      Role     @default(USER)
  posts     Post[]
  profile   Profile?
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  @@index([email])
}

model Profile {
  id     String  @id @default(cuid())
  bio    String?
  avatar String?
  userId String  @unique
  user   User    @relation(fields: [userId], references: [id], onDelete: Cascade)
}

model Post {
  id        String     @id @default(cuid())
  title     String
  content   String?
  published Boolean    @default(false)
  author    User       @relation(fields: [authorId], references: [id])
  authorId  String
  categories Category[]
  createdAt DateTime   @default(now())
  updatedAt DateTime   @updatedAt

  @@index([authorId])
}

model Category {
  id    String @id @default(cuid())
  name  String @unique
  posts Post[]
}

enum Role {
  USER
  ADMIN
}
```

---

### 階段 3: Prisma 客戶端

```typescript
// src/lib/prisma.ts
import { PrismaClient } from '@prisma/client';

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined;
};

export const prisma =
  globalForPrisma.prisma ??
  new PrismaClient({
    log: process.env.NODE_ENV === 'development' ? ['query', 'error', 'warn'] : ['error'],
  });

if (process.env.NODE_ENV !== 'production') {
  globalForPrisma.prisma = prisma;
}

// 擴展型別
export type { User, Post, Profile, Category } from '@prisma/client';
```

---

### 階段 4: Repository 模式

```typescript
// src/repositories/user.repository.ts
import { prisma, User } from '@/lib/prisma';
import { Prisma } from '@prisma/client';

export interface CreateUserData {
  email: string;
  password: string;
  name?: string;
}

export interface UpdateUserData {
  email?: string;
  name?: string;
  role?: 'USER' | 'ADMIN';
}

export interface FindUsersParams {
  page?: number;
  limit?: number;
  search?: string;
  role?: 'USER' | 'ADMIN';
}

export const userRepository = {
  async findById(id: string) {
    return prisma.user.findUnique({
      where: { id },
      include: {
        profile: true,
        _count: { select: { posts: true } },
      },
    });
  },

  async findByEmail(email: string) {
    return prisma.user.findUnique({
      where: { email },
    });
  },

  async findMany({ page = 1, limit = 10, search, role }: FindUsersParams = {}) {
    const where: Prisma.UserWhereInput = {
      ...(search && {
        OR: [
          { email: { contains: search, mode: 'insensitive' } },
          { name: { contains: search, mode: 'insensitive' } },
        ],
      }),
      ...(role && { role }),
    };

    const [users, total] = await Promise.all([
      prisma.user.findMany({
        where,
        skip: (page - 1) * limit,
        take: limit,
        orderBy: { createdAt: 'desc' },
        include: {
          profile: true,
          _count: { select: { posts: true } },
        },
      }),
      prisma.user.count({ where }),
    ]);

    return {
      data: users,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
      },
    };
  },

  async create(data: CreateUserData) {
    return prisma.user.create({
      data,
      include: { profile: true },
    });
  },

  async update(id: string, data: UpdateUserData) {
    return prisma.user.update({
      where: { id },
      data,
      include: { profile: true },
    });
  },

  async delete(id: string) {
    return prisma.user.delete({
      where: { id },
    });
  },

  // 交易範例
  async createWithProfile(
    userData: CreateUserData,
    profileData: { bio?: string; avatar?: string }
  ) {
    return prisma.$transaction(async (tx) => {
      const user = await tx.user.create({
        data: userData,
      });

      const profile = await tx.profile.create({
        data: {
          ...profileData,
          userId: user.id,
        },
      });

      return { ...user, profile };
    });
  },
};
```

---

### 階段 5: Migration 管理

```bash
# 建立 Migration
npx prisma migrate dev --name init

# 重設資料庫
npx prisma migrate reset

# 產生客戶端
npx prisma generate

# 檢視資料庫
npx prisma studio
```

```typescript
// scripts/seed.ts
import { prisma } from '../src/lib/prisma';
import { hash } from 'bcryptjs';

async function main() {
  // 建立管理員
  const adminPassword = await hash('admin123', 12);
  const admin = await prisma.user.upsert({
    where: { email: 'admin@example.com' },
    update: {},
    create: {
      email: 'admin@example.com',
      name: 'Admin',
      password: adminPassword,
      role: 'ADMIN',
    },
  });

  // 建立分類
  const categories = await Promise.all([
    prisma.category.upsert({
      where: { name: 'Technology' },
      update: {},
      create: { name: 'Technology' },
    }),
    prisma.category.upsert({
      where: { name: 'Design' },
      update: {},
      create: { name: 'Design' },
    }),
  ]);

  console.log({ admin, categories });
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
```

---

### 階段 6: 驗證 🔴

**驗證清單**:
- [ ] 資料庫連線正常
- [ ] Migration 執行成功
- [ ] CRUD 操作正常
- [ ] 關聯查詢正確
- [ ] 交易處理正確
- [ ] 索引配置適當

**驗證命令**:
```bash
# 測試連線
npx prisma db pull

# 檢視資料
npx prisma studio

# 執行 Seed
npx prisma db seed
```

🔴 **確認點**: 確認資料庫整合正常

---

## 產出物

| 產出物 | 路徑 |
|--------|------|
| Prisma Schema | `prisma/schema.prisma` |
| Prisma 客戶端 | `src/lib/prisma.ts` |
| Repository | `src/repositories/*.ts` |
| Seed 腳本 | `scripts/seed.ts` |

---

## 相關 Skill

- `/integration-api-client` - API 服務
- `/performance` - 查詢優化

---


## 相關檔案

- SOP 參考: `scenarios/integration/SOP_QuickRef.md`

**基於**: AISDLC v0.09 Integration 情境
