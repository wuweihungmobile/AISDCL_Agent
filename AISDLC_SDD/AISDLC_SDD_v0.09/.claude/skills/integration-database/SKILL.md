---
name: integration-database
description: 資料庫整合，DB Schema Contract 設計先行，ORM 對應資料模型，RTM 追蹤資料完整性 TC
user-invocable: true
disable-model-invocation: false
argument-hint: "<db: postgresql|mysql|mongodb> [orm: prisma|typeorm|jpa|sqlalchemy]"
allowed-tools:
  - Read
  - Write
  - Grep
  - Glob
---

# Integration Database Skill（SDD 原生）

資料庫整合在 SDD 中必須設計先行：DB Schema 必須在實作前以 Contract 形式凍結（對應 SCG-3），ORM 模型從 Schema Contract 生成（非逆向），Business Invariants 必須在 Schema 中強制執行。

---

## 觸發方式

```bash
/integration-database postgresql prisma
/integration-database mysql typeorm
/integration-database postgresql jpa
```

---

## 前置條件（SDD Spec-First）

| 閘門 | 說明 | 驗證方式 |
|------|------|---------|
| 🔷 SCG-3 通過 | DB Schema Contract 已凍結 | `docs/07_design/DB-SCHEMA-CONTRACT-{System}.md` 存在 |
| FRD 資料模型 | 資料結構已定義 | FRD 資料模型章節 |

---

## 執行流程

### 階段 1：DB Schema Contract 確認

讀取 `docs/07_design/DB-SCHEMA-CONTRACT-{System}.md`，確認：
- 所有 Table 已定義（欄位 / 型別 / 約束 / 索引）
- Business Invariants（INV-XXX）有對應的 DB CHECK 約束
- 外鍵關係對應 FRD 資料關係圖

---

### 階段 2：DB Schema ADR（若尚未建立）

呼叫 `/adr-generate "資料庫 Schema 設計"`：

```markdown
# ADR-{NNN}: 資料庫 Schema 策略

## Decision
使用 PostgreSQL + 強型別 Schema（NOT NULL / CHECK 約束）

## Rationale
- CHECK 約束：在 DB 層強制 Business Invariants（INV-XXX）
- NOT NULL：業務必要欄位在 DB 層保護
- 索引策略：依查詢模式設計（對應 NFR-P001）
```

---

### 階段 3：ORM 模型（從 Schema Contract 生成）

**Prisma Schema（從 DB Schema Contract 轉換）**：

```prisma
// prisma/schema.prisma
// 對應 DB-SCHEMA-CONTRACT-{System}.md

model User {
  id        String   @id @default(cuid())
  email     String   @unique                    // INV-001：email 唯一
  name      String                              // NOT NULL（FRD 必要欄位）
  role      UserRole @default(USER)
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  orders Order[]

  @@index([email])                             // 對應 NFR-P001 查詢優化
}

model Order {
  id     String      @id @default(cuid())
  amount Int                                    // 單位：分（避免浮點數）
  status OrderStatus @default(PENDING)
  userId String

  user User @relation(fields: [userId], references: [id])

  @@index([userId, status])                    // 對應查詢模式
}

// Business Invariant 強制（INV-003：金額必須正數）
// 需在 Migration 中加入 CHECK 約束
```

---

### 階段 4：Migration 設計

```sql
-- migrations/{timestamp}_add_business_invariants.sql
-- 對應 Business Invariants（INV-XXX）

-- INV-003：訂單金額必須正數
ALTER TABLE "Order"
  ADD CONSTRAINT "order_amount_positive" CHECK (amount > 0);

-- INV-004：訂單狀態轉換合法性（PENDING → CONFIRMED → COMPLETED）
-- 複雜業務規則在應用層實作，DB 層做基本約束
ALTER TABLE "Order"
  ADD CONSTRAINT "valid_order_status"
  CHECK (status IN ('PENDING', 'CONFIRMED', 'COMPLETED', 'CANCELLED'));
```

---

### 階段 5：RTM 更新 🔴

```bash
/rtm-generate update    # 更新資料完整性 TC（TC-DB-XXX）
/spec-compliance-check docs/07_design/DB-SCHEMA-CONTRACT-{System}.md
```

🔴 確認點：所有 INV-XXX 都有對應 DB 約束；Schema 版本與 Contract 一致。

---

## 強制產出（SDD 文件）

| 產出物 | 路徑 | 對應 SCG |
|--------|------|---------|
| DB Schema ADR | `docs/02_architecture/adr/ADR-{NNN}-db-schema.md` | SCG-3 前 |
| ORM Schema | `prisma/schema.prisma` 或 `src/entities/` | SCG-3 後 |

---

**基於**: AISDLC-SDD v0.01
**DB Schema Contract**: `docs/07_design/DB-SCHEMA-CONTRACT-{System}.md`
