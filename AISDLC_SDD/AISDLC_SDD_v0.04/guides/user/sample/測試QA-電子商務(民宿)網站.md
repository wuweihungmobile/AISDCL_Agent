# 測試與 QA：民宿預訂電子商務網站

> **場景**: Testing & QA - BnB Booking Platform 全面測試與品質保證
> **技術棧**: React (Next.js) + Spring Boot + PostgreSQL + Google Cloud
> **AISDLC 版本**: v0.01
> **更新日期**: 2025-12-16


> **SDD v0.01 使用者提示**：本指南基於 AISDLC-SDD v0.01。使用 AISDLC-SDD v0.01 時，請同時參考對應場景的 SDD Enhancement 文件（`scenarios/{scenario}/SDD_{SCENARIO}_ENHANCEMENT.md`），並確認所有 SCG 閘門步驟已整合到您的工作流程中。

---
---

## 📋 目錄

1. [第一步：Cursor AI 專案路徑設定](#第一步cursor-ai-專案路徑設定)
2. [第二步：AISDLC 框架安裝](#第二步aisdlc-框架安裝)
3. [第三步：Claude Code 完整測試流程](#第三步claude-code-完整測試流程)
4. [附錄：命令速查表](#附錄命令速查表)

---

## 第一步：Cursor AI 專案路徑設定

### 1.1 分析現有專案結構

**假設現有專案結構**:
```
BnB_Booking_Platform/
├── frontend/                       # Next.js 前端
│   ├── app/
│   ├── components/
│   ├── __tests__/                  # ⚠️  前端測試（需補充）
│   ├── package.json
│   └── next.config.js
├── backend/                        # Spring Boot 後端
│   ├── src/
│   │   ├── main/
│   │   └── test/                   # ⚠️  後端測試（需補充）
│   └── pom.xml
└── docker-compose.yml
```

**測試覆蓋率問題**:
- ❌ 前端測試覆蓋率 < 30%
- ❌ 無 E2E 測試（完整訂房流程未測試）
- ❌ 後端 API 測試覆蓋率 < 40%
- ❌ 無整合測試（前後端整合）
- ❌ 無效能測試（高併發訂房）

### 1.2 建立測試專案結構

**在終端機執行**:
```bash
cd ~/Projects/BnB_Booking_Platform

# 前端測試目錄
cd frontend
mkdir -p __tests__/unit
mkdir -p __tests__/integration
mkdir -p __tests__/e2e
mkdir -p cypress/e2e
mkdir -p playwright/tests

# 後端測試目錄
cd ../backend/src
mkdir -p test/java/com/bnb/booking/unit
mkdir -p test/java/com/bnb/booking/integration
mkdir -p test/java/com/bnb/booking/e2e

# 測試報告目錄
cd ../..
mkdir -p test-reports
mkdir -p test-reports/frontend
mkdir -p test-reports/backend
mkdir -p test-reports/e2e
mkdir -p test-reports/coverage

# 文檔目錄
mkdir -p Docs/testing
mkdir -p Docs/test-cases
mkdir -p Docs/reports

# 驗證
tree -L 3 -d
```

**完整專案結構**:
```
BnB_Booking_Platform/
├── frontend/                       # 🎨 Next.js 前端
│   ├── app/
│   ├── components/
│   ├── __tests__/                  # 📝 前端測試
│   │   ├── unit/                   # 單元測試（元件、Hooks）
│   │   ├── integration/            # 整合測試（API 呼叫）
│   │   └── e2e/                    # E2E 測試入口
│   ├── cypress/                    # 🧪 Cypress E2E
│   │   └── e2e/
│   ├── playwright/                 # 🎭 Playwright E2E（備選）
│   │   └── tests/
│   └── package.json
├── backend/                        # ☕ Spring Boot 後端
│   ├── src/
│   │   ├── main/
│   │   └── test/                   # 📝 後端測試
│   │       └── java/com/bnb/booking/
│   │           ├── unit/           # 單元測試（Service、Repository）
│   │           ├── integration/    # 整合測試（Controller、DB）
│   │           └── e2e/            # E2E 測試（完整流程）
│   └── pom.xml
├── test-reports/                   # 📊 測試報告
│   ├── frontend/
│   ├── backend/
│   ├── e2e/
│   └── coverage/
├── Docs/                           # 📄 AISDLC 文檔
│   ├── testing/
│   ├── test-cases/
│   └── reports/
└── AISDLC_SDD_v0.01/                  # 🔴 步驟 2 安裝
```

### 1.3 開啟 Cursor AI

**步驟**:
1. **Cursor AI**: `File` → `Open Folder...` → 選擇 `~/Projects/BnB_Booking_Platform`
2. 確認左側檔案樹顯示完整結構

---

## 第二步：AISDLC 框架安裝

### 2.1 方法一：符號連結（推薦）

```bash
cd ~/Projects/BnB_Booking_Platform

ln -s /Users/wuweihong/Cursor_Project/AISDLC_ALL/AISDLC_v0.09 AISDLC_v0.09

ls -lah | grep AISDLC
```

### 2.2 方法二：複製

```bash
cp -r /Users/wuweihong/Cursor_Project/AISDLC_ALL/AISDLC_v0.09 ~/Projects/BnB_Booking_Platform/

ls AISDLC_SDD_v0.01/
```

### 2.3 驗證安裝

```bash
ls -la AISDLC_SDD_v0.01/AISDLC_INIT.md
cat AISDLC_SDD_v0.01/scenarios/testing/SOP_QuickRef.md | head -50
```

---

## 第三步：Claude Code 完整測試流程

### 階段 1：測試計畫與策略（1 週）

#### 3.1.1 啟動測試計畫 Workflow

**在 Claude Code 輸入**:
```
請載入 AISDLC_INIT.md，我要進行「測試與 QA」場景。

目標：民宿預訂電子商務網站完整測試與品質保證

技術棧：
- 前端：React (Next.js 14) + TypeScript
- 後端：Spring Boot 3.x (Java 17) + PostgreSQL
- 部署：Google Cloud Platform

目前狀況：
1. 前端測試覆蓋率 < 30%
2. 後端 API 測試覆蓋率 < 40%
3. 無 E2E 測試（訂房流程）
4. 無整合測試（前後端整合）
5. 無效能測試（高併發）

請執行「test-planning-and-strategy」workflow，生成完整測試計畫。
```

#### 3.1.2 生成測試計畫

**在 Claude Code 輸入**:
```
請載入 QA Agent (Quincy)，生成測試計畫：

測試範圍：
1. 前端測試（Frontend）
   - 單元測試（元件、Hooks、Utilities）
   - 整合測試（API 呼叫、狀態管理）
   - E2E 測試（使用者流程）

2. 後端測試（Backend）
   - 單元測試（Service、Repository、Domain）
   - 整合測試（Controller、Database）
   - API 測試（REST Endpoints）

3. E2E 測試（End-to-End）
   - 訂房流程（搜尋 → 選擇 → 預訂 → 付款）
   - 房東管理流程（新增房源 → 編輯 → 審核）
   - 使用者認證流程（註冊 → 登入 → OAuth）

4. 非功能性測試（Non-Functional）
   - 效能測試（100+ 併發訂房）
   - 安全性測試（SQL Injection、XSS）
   - 可用性測試（無障礙功能）

請生成測試計畫文檔：`Docs/testing/test-plan.md`
```

**預期輸出** (`Docs/testing/test-plan.md`):
```markdown
# 民宿預訂平台測試計畫

## 測試目標

1. **提升測試覆蓋率**: 從 30% 提升至 80%+
2. **確保功能正確性**: 所有核心功能正常運作
3. **保證系統穩定性**: 高併發下無錯誤
4. **驗證安全性**: 防止 SQL Injection、XSS 攻擊
5. **確保使用者體驗**: 完整流程順暢

## 測試策略

### 測試金字塔

```
        /\
       /  \        E2E Tests (10%)
      /____\       Integration Tests (20%)
     /      \      Unit Tests (70%)
    /________\
```

### 測試優先級

| 優先級 | 測試類型 | 覆蓋率目標 | 執行頻率 |
|--------|---------|----------|---------|
| P0 | 單元測試 | 80%+ | 每次 Commit |
| P1 | 整合測試 | 70%+ | 每次 Push |
| P2 | API 測試 | 90%+ | 每次 Push |
| P3 | E2E 測試 | 關鍵流程 | Release 前 |

## 測試範圍

### 1. 前端測試（70%）

#### 1.1 單元測試（React 元件）
- **元件**: `RoomCard`, `BookingForm`, `SearchBar`, `DatePicker`
- **測試項目**:
  - ✅ 元件渲染正確
  - ✅ Props 傳遞正確
  - ✅ 事件處理（onClick、onChange）
  - ✅ 條件渲染（Loading、Error 狀態）
  - ✅ Hooks 邏輯（useBooking、useSearch）

#### 1.2 整合測試（API 呼叫）
- **測試項目**:
  - ✅ API 呼叫成功（200）
  - ✅ API 錯誤處理（404、500）
  - ✅ 資料映射（DTO → UI Model）
  - ✅ 狀態更新（Redux/Zustand）

#### 1.3 E2E 測試（Cypress/Playwright）
- **測試場景**:
  - ✅ 訂房流程（搜尋 → 選擇 → 預訂 → 付款）
  - ✅ 使用者註冊與登入
  - ✅ 房東新增房源
  - ✅ 跨頁面導航

### 2. 後端測試（20%）

#### 2.1 單元測試（Service Layer）
- **測試類別**: `BookingService`, `RoomService`, `UserService`
- **測試項目**:
  - ✅ 業務邏輯正確性
  - ✅ 輸入驗證（空值、格式）
  - ✅ 邊界條件（日期範圍、價格）
  - ✅ 錯誤處理（Exception）

#### 2.2 整合測試（Controller + DB）
- **測試項目**:
  - ✅ REST API Endpoints
  - ✅ 資料庫 CRUD 操作
  - ✅ Transaction 管理
  - ✅ 認證與授權（JWT）

#### 2.3 Repository 測試（JPA）
- **測試項目**:
  - ✅ CRUD 操作
  - ✅ 查詢方法（JPQL、Native SQL）
  - ✅ 分頁與排序
  - ✅ 外鍵約束

### 3. E2E 測試（10%）

#### 3.1 完整訂房流程
- **測試場景**:
  - ✅ 搜尋民宿（地點、日期、人數）
  - ✅ 查看房源詳情
  - ✅ 選擇房間並預訂
  - ✅ 填寫訂單資訊
  - ✅ 完成付款（模擬）
  - ✅ 確認訂單成功

#### 3.2 房東管理流程
- **測試場景**:
  - ✅ 房東登入
  - ✅ 新增房源（上傳圖片、填寫資訊）
  - ✅ 編輯房源資訊
  - ✅ 查看訂單清單
  - ✅ 審核訂單（接受/拒絕）

## 測試工具

### 前端測試工具

| 測試類型 | 工具 | 版本 |
|---------|------|-----|
| 單元測試 | Jest + React Testing Library | 29.x |
| E2E 測試 | Cypress | 13.x |
| E2E 測試（備選） | Playwright | 1.40.x |
| 視覺測試 | Chromatic / Percy | - |
| 測試覆蓋率 | Istanbul (NYC) | - |

### 後端測試工具

| 測試類型 | 工具 | 版本 |
|---------|------|-----|
| 單元測試 | JUnit 5 | 5.10.x |
| Mock | Mockito | 5.8.x |
| 整合測試 | Spring Boot Test | 3.x |
| API 測試 | REST Assured | 5.4.x |
| Database 測試 | Testcontainers | 1.19.x |
| 測試覆蓋率 | JaCoCo | 0.8.11 |

## 測試時程

| 階段 | 週數 | 交付項目 |
|------|-----|---------|
| 1. 測試計畫 | 1 週 | 測試計畫文檔、測試案例 |
| 2. 前端單元測試 | 2 週 | 80%+ 覆蓋率 |
| 3. 後端單元測試 | 2 週 | 80%+ 覆蓋率 |
| 4. 整合測試 | 1.5 週 | API + Database 測試 |
| 5. E2E 測試 | 2 週 | 關鍵流程測試 |
| 6. 效能測試 | 1 週 | 100+ 併發測試 |
| 7. 測試報告 | 0.5 週 | 測試報告、改善建議 |

**總計**: 10 週

## 測試環境

| 環境 | 用途 | 配置 |
|------|-----|------|
| 本地開發 | 單元測試、整合測試 | Docker Compose |
| CI/CD | 自動化測試 | GitHub Actions |
| Staging | E2E 測試 | Google Cloud Run |
| Production | 監控與回歸測試 | Google Cloud |

## 成功標準

- ✅ 前端測試覆蓋率 > 80%
- ✅ 後端測試覆蓋率 > 80%
- ✅ API 測試覆蓋率 > 90%
- ✅ 所有 P0/P1 測試通過率 100%
- ✅ 無 Critical/High 級別 Bug
- ✅ CI/CD 測試執行時間 < 15 分鐘
- ✅ E2E 測試關鍵流程 100% 通過
```

---

### 階段 2：前端單元測試（2 週）

#### 3.2.1 配置前端測試依賴

**在 Claude Code 輸入**:
```
請配置前端測試依賴，包含：

1. Jest + React Testing Library
2. @testing-library/user-event
3. msw（Mock Service Worker）
4. jest-environment-jsdom

請更新 `frontend/package.json` 和創建 `jest.config.js`
```

**Claude Code 生成** (`frontend/package.json`):
```json
{
  "name": "bnb-booking-frontend",
  "version": "1.0.0",
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage",
    "test:e2e": "cypress run",
    "test:e2e:open": "cypress open"
  },
  "dependencies": {
    "next": "14.0.4",
    "react": "18.2.0",
    "react-dom": "18.2.0",
    "typescript": "5.3.3"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.1.5",
    "@testing-library/react": "^14.1.2",
    "@testing-library/user-event": "^14.5.1",
    "@types/jest": "^29.5.11",
    "cypress": "^13.6.2",
    "jest": "^29.7.0",
    "jest-environment-jsdom": "^29.7.0",
    "msw": "^2.0.11"
  }
}
```

**Claude Code 生成** (`frontend/jest.config.js`):
```javascript
const nextJest = require('next/jest')

const createJestConfig = nextJest({
  dir: './',
})

const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testEnvironment: 'jest-environment-jsdom',
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
  collectCoverageFrom: [
    'app/**/*.{js,jsx,ts,tsx}',
    'components/**/*.{js,jsx,ts,tsx}',
    '!**/*.d.ts',
    '!**/node_modules/**',
    '!**/.next/**',
  ],
  coverageThreshold: {
    global: {
      branches: 70,
      functions: 70,
      lines: 80,
      statements: 80,
    },
  },
}

module.exports = createJestConfig(customJestConfig)
```

#### 3.2.2 React 元件單元測試

**在 Claude Code 輸入**:
```
請為 RoomCard 元件編寫完整單元測試：

元件功能：
- 顯示房源圖片、標題、價格
- 點擊卡片跳轉到房源詳情頁
- 顯示評分與評論數
- 顯示設施標籤（WiFi、停車場等）

測試項目：
1. 元件渲染正確
2. Props 正確傳遞
3. 點擊事件正確觸發
4. 條件渲染（有/無評分）
5. 價格格式化顯示

請生成測試檔案：`frontend/__tests__/unit/components/RoomCard.test.tsx`
```

**Claude Code 生成** (`RoomCard.test.tsx`):
```typescript
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import RoomCard from '@/components/RoomCard'

describe('RoomCard', () => {
  const mockRoom = {
    id: 1,
    title: '溫馨雙人房',
    price: 2500,
    rating: 4.8,
    reviewCount: 128,
    imageUrl: '/rooms/room1.jpg',
    amenities: ['WiFi', '停車場', '早餐'],
  }

  const mockOnClick = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  // ==================== 渲染測試 ====================

  it('應該正確渲染房源資訊', () => {
    render(<RoomCard room={mockRoom} onClick={mockOnClick} />)

    // 驗證標題
    expect(screen.getByText('溫馨雙人房')).toBeInTheDocument()

    // 驗證價格
    expect(screen.getByText('$2,500 / 晚')).toBeInTheDocument()

    // 驗證評分
    expect(screen.getByText('4.8')).toBeInTheDocument()
    expect(screen.getByText('(128 則評論)')).toBeInTheDocument()

    // 驗證圖片
    const image = screen.getByAltText('溫馨雙人房')
    expect(image).toHaveAttribute('src', '/rooms/room1.jpg')
  })

  it('應該正確顯示設施標籤', () => {
    render(<RoomCard room={mockRoom} onClick={mockOnClick} />)

    expect(screen.getByText('WiFi')).toBeInTheDocument()
    expect(screen.getByText('停車場')).toBeInTheDocument()
    expect(screen.getByText('早餐')).toBeInTheDocument()
  })

  // ==================== 互動測試 ====================

  it('點擊卡片應該觸發 onClick 事件', () => {
    render(<RoomCard room={mockRoom} onClick={mockOnClick} />)

    const card = screen.getByTestId('room-card')
    fireEvent.click(card)

    expect(mockOnClick).toHaveBeenCalledTimes(1)
    expect(mockOnClick).toHaveBeenCalledWith(mockRoom.id)
  })

  // ==================== 條件渲染測試 ====================

  it('無評分時應該顯示「尚無評論」', () => {
    const roomWithoutRating = {
      ...mockRoom,
      rating: null,
      reviewCount: 0,
    }

    render(<RoomCard room={roomWithoutRating} onClick={mockOnClick} />)

    expect(screen.getByText('尚無評論')).toBeInTheDocument()
    expect(screen.queryByText('4.8')).not.toBeInTheDocument()
  })

  it('價格為 0 時應該顯示「面議」', () => {
    const freeRoom = {
      ...mockRoom,
      price: 0,
    }

    render(<RoomCard room={freeRoom} onClick={mockOnClick} />)

    expect(screen.getByText('面議')).toBeInTheDocument()
  })

  // ==================== 格式化測試 ====================

  it('應該正確格式化大額價格', () => {
    const expensiveRoom = {
      ...mockRoom,
      price: 15000,
    }

    render(<RoomCard room={expensiveRoom} onClick={mockOnClick} />)

    expect(screen.getByText('$15,000 / 晚')).toBeInTheDocument()
  })

  // ==================== 無障礙測試 ====================

  it('應該有正確的 ARIA 標籤', () => {
    render(<RoomCard room={mockRoom} onClick={mockOnClick} />)

    const card = screen.getByRole('article')
    expect(card).toHaveAttribute('aria-label', '溫馨雙人房房源卡片')

    const rating = screen.getByLabelText('評分 4.8 分，共 128 則評論')
    expect(rating).toBeInTheDocument()
  })
})
```

#### 3.2.3 API 整合測試（MSW）

**在 Claude Code 輸入**:
```
請為訂房 API 呼叫編寫整合測試，使用 MSW 模擬後端：

API Endpoint: POST /api/bookings
功能: 創建新訂單

測試項目：
1. API 呼叫成功（200）
2. API 錯誤處理（400、500）
3. 資料映射（Request/Response DTO）
4. Loading 狀態管理

請生成：
1. MSW Handler: `frontend/mocks/handlers.ts`
2. 測試檔案: `frontend/__tests__/integration/api/booking.test.ts`
```

**Claude Code 生成** (`mocks/handlers.ts`):
```typescript
import { rest } from 'msw'

export const handlers = [
  // 創建訂單 - 成功
  rest.post('/api/bookings', (req, res, ctx) => {
    const { roomId, checkIn, checkOut, guestCount } = req.body as any

    if (!roomId || !checkIn || !checkOut) {
      return res(
        ctx.status(400),
        ctx.json({ error: '缺少必要欄位' })
      )
    }

    return res(
      ctx.status(201),
      ctx.json({
        id: 123,
        roomId,
        checkIn,
        checkOut,
        guestCount,
        totalPrice: 7500,
        status: 'PENDING',
        createdAt: new Date().toISOString(),
      })
    )
  }),

  // 查詢訂單
  rest.get('/api/bookings/:id', (req, res, ctx) => {
    const { id } = req.params

    return res(
      ctx.status(200),
      ctx.json({
        id: Number(id),
        roomId: 1,
        checkIn: '2025-01-15',
        checkOut: '2025-01-18',
        guestCount: 2,
        totalPrice: 7500,
        status: 'CONFIRMED',
      })
    )
  }),

  // 模擬伺服器錯誤
  rest.post('/api/bookings/error', (req, res, ctx) => {
    return res(
      ctx.status(500),
      ctx.json({ error: '伺服器錯誤' })
    )
  }),
]
```

**Claude Code 生成** (`booking.test.ts`):
```typescript
import { rest } from 'msw'
import { setupServer } from 'msw/node'
import { handlers } from '@/mocks/handlers'
import { createBooking, getBooking } from '@/services/bookingService'

const server = setupServer(...handlers)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('Booking API Integration', () => {
  describe('createBooking', () => {
    it('應該成功創建訂單', async () => {
      const bookingData = {
        roomId: 1,
        checkIn: '2025-01-15',
        checkOut: '2025-01-18',
        guestCount: 2,
      }

      const result = await createBooking(bookingData)

      expect(result.success).toBe(true)
      expect(result.data).toMatchObject({
        id: 123,
        roomId: 1,
        totalPrice: 7500,
        status: 'PENDING',
      })
    })

    it('應該處理驗證錯誤（400）', async () => {
      const invalidData = {
        roomId: null,
        checkIn: '',
        checkOut: '',
        guestCount: 0,
      }

      const result = await createBooking(invalidData)

      expect(result.success).toBe(false)
      expect(result.error).toBe('缺少必要欄位')
    })

    it('應該處理伺服器錯誤（500）', async () => {
      server.use(
        rest.post('/api/bookings', (req, res, ctx) => {
          return res(ctx.status(500), ctx.json({ error: '伺服器錯誤' }))
        })
      )

      const bookingData = {
        roomId: 1,
        checkIn: '2025-01-15',
        checkOut: '2025-01-18',
        guestCount: 2,
      }

      const result = await createBooking(bookingData)

      expect(result.success).toBe(false)
      expect(result.error).toBe('伺服器錯誤')
    })
  })

  describe('getBooking', () => {
    it('應該成功查詢訂單', async () => {
      const result = await getBooking(123)

      expect(result.success).toBe(true)
      expect(result.data).toMatchObject({
        id: 123,
        roomId: 1,
        status: 'CONFIRMED',
      })
    })
  })
})
```

---

### 階段 3：後端單元測試（2 週）

#### 3.3.1 配置後端測試依賴

**在 Claude Code 輸入**:
```
請配置後端測試依賴，包含：

1. JUnit 5
2. Mockito
3. Spring Boot Test
4. Testcontainers（PostgreSQL）
5. REST Assured

請更新 `backend/pom.xml`
```

**Claude Code 生成** (`backend/pom.xml`):
```xml
<dependencies>
    <!-- 主程式依賴 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-jpa</artifactId>
    </dependency>
    <dependency>
        <groupId>org.postgresql</groupId>
        <artifactId>postgresql</artifactId>
    </dependency>

    <!-- ==================== 測試依賴 ==================== -->

    <!-- JUnit 5 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>

    <!-- Mockito -->
    <dependency>
        <groupId>org.mockito</groupId>
        <artifactId>mockito-core</artifactId>
        <scope>test</scope>
    </dependency>

    <!-- REST Assured（API 測試） -->
    <dependency>
        <groupId>io.rest-assured</groupId>
        <artifactId>rest-assured</artifactId>
        <version>5.4.0</version>
        <scope>test</scope>
    </dependency>

    <!-- Testcontainers（Docker 測試容器） -->
    <dependency>
        <groupId>org.testcontainers</groupId>
        <artifactId>testcontainers</artifactId>
        <version>1.19.3</version>
        <scope>test</scope>
    </dependency>
    <dependency>
        <groupId>org.testcontainers</groupId>
        <artifactId>postgresql</artifactId>
        <version>1.19.3</version>
        <scope>test</scope>
    </dependency>
    <dependency>
        <groupId>org.testcontainers</groupId>
        <artifactId>junit-jupiter</artifactId>
        <version>1.19.3</version>
        <scope>test</scope>
    </dependency>

    <!-- AssertJ（流暢斷言庫） -->
    <dependency>
        <groupId>org.assertj</groupId>
        <artifactId>assertj-core</artifactId>
        <scope>test</scope>
    </dependency>
</dependencies>

<build>
    <plugins>
        <!-- JaCoCo 測試覆蓋率 -->
        <plugin>
            <groupId>org.jacoco</groupId>
            <artifactId>jacoco-maven-plugin</artifactId>
            <version>0.8.11</version>
            <executions>
                <execution>
                    <goals>
                        <goal>prepare-agent</goal>
                    </goals>
                </execution>
                <execution>
                    <id>report</id>
                    <phase>test</phase>
                    <goals>
                        <goal>report</goal>
                    </goals>
                </execution>
            </executions>
        </plugin>
    </plugins>
</build>
```

#### 3.3.2 Service 層單元測試

**在 Claude Code 輸入**:
```
請為 BookingService 編寫完整單元測試：

Service 功能：
- createBooking: 創建訂單
- getBookingById: 查詢訂單
- cancelBooking: 取消訂單
- calculateTotalPrice: 計算總價

測試項目：
1. 創建訂單（成功/失敗）
2. 驗證輸入（日期範圍、人數）
3. 計算總價（夜數、價格）
4. 取消訂單（狀態檢查）

請生成測試檔案：`backend/src/test/java/com/bnb/booking/service/BookingServiceTest.java`
```

**Claude Code 生成** (`BookingServiceTest.java`):
```java
package com.bnb.booking.service;

import com.bnb.booking.domain.Booking;
import com.bnb.booking.domain.Room;
import com.bnb.booking.domain.BookingStatus;
import com.bnb.booking.repository.BookingRepository;
import com.bnb.booking.repository.RoomRepository;
import com.bnb.booking.dto.CreateBookingRequest;
import com.bnb.booking.exception.BookingException;
import com.bnb.booking.exception.RoomNotFoundException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDate;
import java.util.Optional;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
@DisplayName("BookingService 單元測試")
class BookingServiceTest {

    @Mock
    private BookingRepository bookingRepository;

    @Mock
    private RoomRepository roomRepository;

    @InjectMocks
    private BookingService bookingService;

    private Room testRoom;
    private CreateBookingRequest validRequest;

    @BeforeEach
    void setUp() {
        testRoom = Room.builder()
                .id(1L)
                .title("溫馨雙人房")
                .pricePerNight(2500)
                .maxGuests(2)
                .build();

        validRequest = CreateBookingRequest.builder()
                .roomId(1L)
                .checkIn(LocalDate.now().plusDays(7))
                .checkOut(LocalDate.now().plusDays(10))
                .guestCount(2)
                .build();
    }

    // ==================== 創建訂單測試 ====================

    @Test
    @DisplayName("應該成功創建訂單")
    void shouldCreateBookingSuccessfully() {
        // Given
        when(roomRepository.findById(1L)).thenReturn(Optional.of(testRoom));
        when(bookingRepository.save(any(Booking.class))).thenAnswer(invocation -> {
            Booking booking = invocation.getArgument(0);
            booking.setId(100L);
            return booking;
        });

        // When
        Booking result = bookingService.createBooking(validRequest);

        // Then
        assertThat(result).isNotNull();
        assertThat(result.getId()).isEqualTo(100L);
        assertThat(result.getRoom()).isEqualTo(testRoom);
        assertThat(result.getCheckIn()).isEqualTo(validRequest.getCheckIn());
        assertThat(result.getCheckOut()).isEqualTo(validRequest.getCheckOut());
        assertThat(result.getStatus()).isEqualTo(BookingStatus.PENDING);

        verify(roomRepository, times(1)).findById(1L);
        verify(bookingRepository, times(1)).save(any(Booking.class));
    }

    @Test
    @DisplayName("房源不存在時應該拋出例外")
    void shouldThrowExceptionWhenRoomNotFound() {
        // Given
        when(roomRepository.findById(1L)).thenReturn(Optional.empty());

        // When & Then
        assertThatThrownBy(() -> bookingService.createBooking(validRequest))
                .isInstanceOf(RoomNotFoundException.class)
                .hasMessage("找不到房源 ID: 1");

        verify(bookingRepository, never()).save(any());
    }

    @Test
    @DisplayName("入住日期早於今天應該拋出例外")
    void shouldThrowExceptionWhenCheckInDateIsInThePast() {
        // Given
        CreateBookingRequest invalidRequest = CreateBookingRequest.builder()
                .roomId(1L)
                .checkIn(LocalDate.now().minusDays(1))
                .checkOut(LocalDate.now().plusDays(3))
                .guestCount(2)
                .build();

        // When & Then
        assertThatThrownBy(() -> bookingService.createBooking(invalidRequest))
                .isInstanceOf(BookingException.class)
                .hasMessage("入住日期不可早於今天");

        verify(bookingRepository, never()).save(any());
    }

    @Test
    @DisplayName("退房日期早於入住日期應該拋出例外")
    void shouldThrowExceptionWhenCheckOutBeforeCheckIn() {
        // Given
        CreateBookingRequest invalidRequest = CreateBookingRequest.builder()
                .roomId(1L)
                .checkIn(LocalDate.now().plusDays(10))
                .checkOut(LocalDate.now().plusDays(7))
                .guestCount(2)
                .build();

        // When & Then
        assertThatThrownBy(() -> bookingService.createBooking(invalidRequest))
                .isInstanceOf(BookingException.class)
                .hasMessage("退房日期必須晚於入住日期");
    }

    @Test
    @DisplayName("人數超過房間上限應該拋出例外")
    void shouldThrowExceptionWhenGuestCountExceedsLimit() {
        // Given
        CreateBookingRequest invalidRequest = CreateBookingRequest.builder()
                .roomId(1L)
                .checkIn(LocalDate.now().plusDays(7))
                .checkOut(LocalDate.now().plusDays(10))
                .guestCount(5)  // 超過上限 2 人
                .build();

        when(roomRepository.findById(1L)).thenReturn(Optional.of(testRoom));

        // When & Then
        assertThatThrownBy(() -> bookingService.createBooking(invalidRequest))
                .isInstanceOf(BookingException.class)
                .hasMessage("入住人數超過房間上限（最多 2 人）");
    }

    // ==================== 計算總價測試 ====================

    @Test
    @DisplayName("應該正確計算總價（3 晚 x 2500 = 7500）")
    void shouldCalculateTotalPriceCorrectly() {
        // Given
        LocalDate checkIn = LocalDate.of(2025, 1, 15);
        LocalDate checkOut = LocalDate.of(2025, 1, 18);  // 3 晚

        // When
        int totalPrice = bookingService.calculateTotalPrice(testRoom, checkIn, checkOut);

        // Then
        assertThat(totalPrice).isEqualTo(7500);  // 2500 x 3
    }

    @Test
    @DisplayName("應該正確計算總價（1 晚）")
    void shouldCalculateTotalPriceForOneNight() {
        // Given
        LocalDate checkIn = LocalDate.of(2025, 1, 15);
        LocalDate checkOut = LocalDate.of(2025, 1, 16);  // 1 晚

        // When
        int totalPrice = bookingService.calculateTotalPrice(testRoom, checkIn, checkOut);

        // Then
        assertThat(totalPrice).isEqualTo(2500);
    }

    // ==================== 取消訂單測試 ====================

    @Test
    @DisplayName("應該成功取消 PENDING 狀態的訂單")
    void shouldCancelPendingBooking() {
        // Given
        Booking booking = Booking.builder()
                .id(100L)
                .status(BookingStatus.PENDING)
                .build();

        when(bookingRepository.findById(100L)).thenReturn(Optional.of(booking));

        // When
        bookingService.cancelBooking(100L);

        // Then
        assertThat(booking.getStatus()).isEqualTo(BookingStatus.CANCELLED);
        verify(bookingRepository, times(1)).save(booking);
    }

    @Test
    @DisplayName("已確認的訂單無法取消")
    void shouldNotCancelConfirmedBooking() {
        // Given
        Booking booking = Booking.builder()
                .id(100L)
                .status(BookingStatus.CONFIRMED)
                .build();

        when(bookingRepository.findById(100L)).thenReturn(Optional.of(booking));

        // When & Then
        assertThatThrownBy(() -> bookingService.cancelBooking(100L))
                .isInstanceOf(BookingException.class)
                .hasMessage("已確認的訂單無法取消");

        verify(bookingRepository, never()).save(any());
    }
}
```

---

### 階段 4：E2E 測試（2 週）

#### 3.4.1 Cypress E2E 測試

**在 Claude Code 輸入**:
```
請編寫完整訂房流程的 E2E 測試（Cypress）：

測試場景：
1. 搜尋民宿（地點、日期、人數）
2. 查看房源清單
3. 點擊房源查看詳情
4. 選擇日期並預訂
5. 填寫訂單資訊
6. 確認訂單成功

請生成測試檔案：`frontend/cypress/e2e/booking-flow.cy.ts`
```

**Claude Code 生成** (`booking-flow.cy.ts`):
```typescript
describe('完整訂房流程 E2E 測試', () => {
  beforeEach(() => {
    cy.visit('http://localhost:3000')
  })

  it('應該成功完成完整訂房流程', () => {
    // ✅ 步驟 1: 搜尋民宿
    cy.get('[data-cy=search-location]').type('台北市')
    cy.get('[data-cy=search-checkin]').type('2025-01-15')
    cy.get('[data-cy=search-checkout]').type('2025-01-18')
    cy.get('[data-cy=search-guests]').select('2')
    cy.get('[data-cy=search-button]').click()

    // ✅ 步驟 2: 等待搜尋結果
    cy.url().should('include', '/search')
    cy.get('[data-cy=room-card]').should('have.length.greaterThan', 0)

    // ✅ 步驟 3: 查看第一個房源詳情
    cy.get('[data-cy=room-card]').first().click()
    cy.url().should('include', '/rooms/')

    // ✅ 步驟 4: 驗證房源詳情頁
    cy.get('[data-cy=room-title]').should('be.visible')
    cy.get('[data-cy=room-price]').should('contain', '$')
    cy.get('[data-cy=room-gallery]').should('be.visible')

    // ✅ 步驟 5: 選擇日期並預訂
    cy.get('[data-cy=booking-checkin]').should('have.value', '2025-01-15')
    cy.get('[data-cy=booking-checkout]').should('have.value', '2025-01-18')
    cy.get('[data-cy=booking-guests]').select('2')
    cy.get('[data-cy=booking-total-price]').should('contain', '$7,500')

    cy.get('[data-cy=booking-button]').click()

    // ✅ 步驟 6: 填寫訂單資訊
    cy.url().should('include', '/checkout')

    cy.get('[data-cy=guest-name]').type('王小明')
    cy.get('[data-cy=guest-email]').type('test@example.com')
    cy.get('[data-cy=guest-phone]').type('0912345678')
    cy.get('[data-cy=special-requests]').type('請提供嬰兒床')

    // ✅ 步驟 7: 確認訂單
    cy.get('[data-cy=confirm-button]').click()

    // ✅ 步驟 8: 驗證成功頁面
    cy.url().should('include', '/booking/success')
    cy.get('[data-cy=success-message]').should('contain', '訂房成功')
    cy.get('[data-cy=booking-number]').should('be.visible')
    cy.get('[data-cy=booking-details]').should('contain', '王小明')
  })

  it('應該驗證必填欄位', () => {
    // 直接進入訂單頁面（模擬）
    cy.visit('http://localhost:3000/checkout')

    // 不填寫任何欄位，直接送出
    cy.get('[data-cy=confirm-button]').click()

    // 驗證錯誤訊息
    cy.get('[data-cy=error-name]').should('contain', '請輸入姓名')
    cy.get('[data-cy=error-email]').should('contain', '請輸入 Email')
    cy.get('[data-cy=error-phone]').should('contain', '請輸入電話')
  })

  it('應該處理已被預訂的情況', () => {
    // 模擬房源已被預訂
    cy.intercept('POST', '/api/bookings', {
      statusCode: 400,
      body: { error: '此房源在選定日期已被預訂' },
    }).as('createBooking')

    cy.visit('http://localhost:3000/rooms/1')
    cy.get('[data-cy=booking-button]').click()

    // 填寫訂單資訊
    cy.get('[data-cy=guest-name]').type('王小明')
    cy.get('[data-cy=guest-email]').type('test@example.com')
    cy.get('[data-cy=guest-phone]').type('0912345678')
    cy.get('[data-cy=confirm-button]').click()

    // 驗證錯誤訊息
    cy.wait('@createBooking')
    cy.get('[data-cy=error-message]').should('contain', '此房源在選定日期已被預訂')
  })
})
```

---

### 階段 5：測試報告與改善（0.5 週）

**在 Claude Code 輸入**:
```
請生成測試報告：

1. 測試覆蓋率報告
2. 測試結果彙總
3. Bug 清單
4. 改善建議

輸出文檔：`Docs/reports/testing-final-report.md`
```

**執行所有測試**:
```bash
# 前端測試
cd frontend
npm run test:coverage

# 後端測試
cd ../backend
mvn clean test jacoco:report

# E2E 測試
cd ../frontend
npm run test:e2e

# 查看覆蓋率報告
open frontend/coverage/lcov-report/index.html
open backend/target/site/jacoco/index.html
```

---

## 附錄：命令速查表

### 前端測試

```bash
# 單元測試
npm run test

# 單元測試（Watch 模式）
npm run test:watch

# 測試覆蓋率
npm run test:coverage

# E2E 測試（Headless）
npm run test:e2e

# E2E 測試（Interactive）
npm run test:e2e:open
```

### 後端測試

```bash
# 所有測試
mvn test

# 特定測試類別
mvn test -Dtest=BookingServiceTest

# 測試覆蓋率
mvn test jacoco:report

# 查看覆蓋率報告
open target/site/jacoco/index.html
```

### CI/CD 整合（GitHub Actions）

```yaml
name: Test

on: [push, pull_request]

jobs:
  frontend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: cd frontend && npm ci
      - run: cd frontend && npm run test:coverage
      - uses: codecov/codecov-action@v3

  backend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-java@v3
        with:
          java-version: '17'
      - run: cd backend && mvn test jacoco:report
      - uses: codecov/codecov-action@v3

  e2e-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: cypress-io/github-action@v6
        with:
          working-directory: frontend
          start: npm run dev
          wait-on: 'http://localhost:3000'
```

---

## 🎯 測試時程表（總計 10 週）

| 階段 | 週數 | 主要工作 |
|------|-----|---------|
| 1. 測試計畫 | 1 週 | 測試計畫、測試案例設計 |
| 2. 前端單元測試 | 2 週 | React 元件、Hooks、API 整合 |
| 3. 後端單元測試 | 2 週 | Service、Repository、Controller |
| 4. 整合測試 | 1.5 週 | API + Database 測試 |
| 5. E2E 測試 | 2 週 | 完整業務流程測試 |
| 6. 效能測試 | 1 週 | 100+ 併發測試 |
| 7. 測試報告 | 0.5 週 | 測試報告、改善建議 |

---

## 📚 相關文檔

- [AISDLC_INIT.md](../../AISDLC_INIT.md)
- [test-planning-and-strategy.md](../../workflow/scenario-specific/test-planning-and-strategy.md)
- [Testing SOP](../../scenarios/testing/SOP.md)
- [Jest 文檔](https://jestjs.io/)
- [Cypress 文檔](https://www.cypress.io/)
- [Spring Boot Testing](https://spring.io/guides/gs/testing-web/)

---

**版本**: 1.0
**作者**: AISDLC Framework Team
**最後更新**: 2025-12-16
